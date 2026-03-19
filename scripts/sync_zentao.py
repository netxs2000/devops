"""手动触发禅道数据同步脚本 (支持 Task 与 Effort)"""

import logging
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# 添加项目根目录到路径
sys.path.append(os.getcwd())

# Ensure all models are loaded for SQLAlchemy mapper initialization
from sqlalchemy.orm import configure_mappers

import devops_collector.models


try:
    configure_mappers()
except Exception:
    # 可能已经在别处初始化过了
    pass

from devops_collector.config import settings
from devops_collector.plugins.zentao.client import ZenTaoClient
from devops_collector.plugins.zentao.models import ZenTaoProduct
from devops_collector.plugins.zentao.worker import ZenTaoWorker


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SyncZenTao")


def sync_all_zentao_products():
    engine = create_engine(settings.database.uri)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 初始化客户端
        client = ZenTaoClient(
            url=settings.zentao.url,
            token=settings.zentao.token,
            account=settings.zentao.account,
            password=settings.zentao.password,
        )
        worker = ZenTaoWorker(session, client)

        # 获取数据库中所有已注册的禅道产品
        products = session.query(ZenTaoProduct).all()

        if not products:
            logger.info("数据库中未发现禅道产品，正在从 API 自动发现...")
            try:
                remote_products = client.get_products()
                for p_data in remote_products:
                    try:
                        logger.info(f"发现远程产品: {p_data['name']} (ID: {p_data['id']})")
                        worker._sync_product(p_data["id"])
                        session.commit()  # 发现一个存一个
                    except Exception as pe:
                        logger.warning(f"同步产品元数据失败 (ID: {p_data['id']}): {pe}")
                        session.rollback()
                # 重新查询
                products = session.query(ZenTaoProduct).all()
            except Exception as e:
                logger.error(f"从 API 获取产品列表失败: {e}")
                return

        if not products:
            logger.warning("未找到任何禅道产品。")
            return

        for p in products:
            logger.info(f"开始同步产品: {p.name} (ID: {p.id})")
            task = {"product_id": p.id}
            worker.process_task(task)
            logger.info(f"产品 {p.name} 同步完成！")
            session.commit()  # 每个产品同步完提交一次

    except Exception as e:
        logger.error(f"同步失败: {e}")
        import traceback

        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 如果传了参数，则只同步特定产品
        engine = create_engine(settings.database.uri)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            client = ZenTaoClient(
                url=settings.zentao.url,
                token=settings.zentao.token,
                account=settings.zentao.account,
                password=settings.zentao.password,
            )
            worker = ZenTaoWorker(session, client)
            pid = int(sys.argv[1])
            logger.info(f"手动触发产品 ID 同步: {pid}")
            worker.process_task({"product_id": pid})
            session.commit()
            logger.info("同步成功！")
        except Exception as e:
            logger.error(f"同步失败: {e}")
        finally:
            session.close()
    else:
        sync_all_zentao_products()
