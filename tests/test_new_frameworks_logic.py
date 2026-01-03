
import unittest
import sqlite3
from datetime import datetime, timedelta

class TestNewFrameworksLogic(unittest.TestCase):
    
    def setUp(self):
        # 1. Setup In-Memory Database
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        
        # 2. Schema Setup (Mocking the real tables needed for Views)
        # Projects Table
        self.cursor.execute("""
            CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT);
        """)
        
        # Issues Table (Source for Flow Framework)
        self.cursor.execute("""
            CREATE TABLE issues (
                id INTEGER PRIMARY KEY,
                project_id INTEGER,
                title TEXT,
                state TEXT,
                labels TEXT,
                created_at DATETIME,
                closed_at DATETIME
            );
        """)
        
        
        # Satisfaction Table (Source for SPACE - S)
        self.cursor.execute("""
            CREATE TABLE satisfaction_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT,
                score INTEGER,
                date DATE,
                tags TEXT
            );
        """)
        
        # --- Hotspot Analysis Tables ---
        self.cursor.execute("CREATE TABLE commits (id TEXT PRIMARY KEY, project_id INTEGER, committed_date DATETIME);")
        self.cursor.execute("CREATE TABLE commit_file_stats (id INTEGER PRIMARY KEY, commit_id TEXT, file_path TEXT, code_added INTEGER, code_deleted INTEGER);")

        # 3. Apply SQL Logics ( The Views )
        
        # View: Code Hotspots (Michael Feathers)
        # Adapted from HOTSPOTS.sql for SQLite
        self.cursor.execute("""
        CREATE VIEW view_file_hotspots AS
        SELECT 
            f.file_path,
            -- Churn Frequency (Modifications in last 90 days)
            COUNT(DISTINCT CASE WHEN c.committed_date >= DATE('now', '-90 days') THEN f.commit_id END) as churn_90d,
            -- Complexity Proxy (Net Lines of Code Accumulated)
            ABS(SUM(f.code_added) - SUM(f.code_deleted)) as estimated_loc,
            -- Context
            MAX(c.committed_date) as last_modified_at
        FROM 
            commit_file_stats f
        JOIN 
            commits c ON f.commit_id = c.id
        GROUP BY 
            f.file_path
        HAVING 
            estimated_loc > 0;
        """)
        
        # View 1: Standardization
        self.cursor.execute("""
        CREATE VIEW view_flow_items AS
        SELECT
            i.id, i.project_id, p.name as project_name, i.title, i.state, i.created_at, i.closed_at,
            CASE 
                WHEN i.labels LIKE '%security%' OR i.labels LIKE '%risk%' THEN 'Risk'
                WHEN i.labels LIKE '%bug%' OR i.labels LIKE '%fix%' THEN 'Defect'
                WHEN i.labels LIKE '%refactor%' OR i.labels LIKE '%debt%' THEN 'Debt'
                ELSE 'Feature' 
            END as flow_type,
            CASE 
                WHEN i.closed_at IS NOT NULL THEN (JULIANDAY(i.closed_at) - JULIANDAY(i.created_at))
                ELSE NULL 
            END as flow_time_days
        FROM issues i
        LEFT JOIN projects p ON i.project_id = p.id;
        """)
        
        # View 2: Aggregation
        self.cursor.execute("""
        CREATE VIEW view_flow_metrics_weekly AS
        SELECT
            STRFTIME('%Y-%W', i.created_at) as week_identifier,
            MIN(DATE(i.created_at, 'weekday 0', '-6 days')) as week_start_date,
            SUM(CASE WHEN flow_type='Feature' AND state='closed' THEN 1 ELSE 0 END) as closed_features,
            SUM(CASE WHEN flow_type='Defect' AND state='closed' THEN 1 ELSE 0 END) as closed_defects,
            SUM(CASE WHEN flow_type='Debt' AND state='closed' THEN 1 ELSE 0 END) as closed_debts,
            SUM(CASE WHEN flow_type='Risk' AND state='closed' THEN 1 ELSE 0 END) as closed_risks,
            COUNT(CASE WHEN state='closed' THEN 1 END) as flow_velocity,
            AVG(flow_time_days) as avg_flow_time_days
        FROM view_flow_items i
        GROUP BY 1;
        """)

    def tearDown(self):
        self.conn.close()


    def test_flow_item_categorization(self):
        """Test if Flow Framework correctly categorizes Items based on labels."""
        print("\n--- Testing Flow Framework: Categorization Logic ---")
        
        # Insert Sample Data
        self.cursor.execute("INSERT INTO issues (project_id, labels, state) VALUES (1, 'story,ui', 'closed')")
        self.cursor.execute("INSERT INTO issues (project_id, labels, state) VALUES (1, 'bug,critical', 'closed')")
        self.cursor.execute("INSERT INTO issues (project_id, labels, state) VALUES (1, 'refactor,backend', 'closed')")
        self.cursor.execute("INSERT INTO issues (project_id, labels, state) VALUES (1, 'bug,security', 'closed')")
        
        self.conn.commit()
        
        # Verification
        self.cursor.execute("SELECT flow_type, COUNT(*) as cnt FROM view_flow_items GROUP BY flow_type")
        results = dict(self.cursor.fetchall())
        print(f"Distribution: {results}")
        
        # Assertions
        self.assertEqual(results.get('Feature'), 1)
        self.assertEqual(results.get('Defect'), 1)
        self.assertEqual(results.get('Debt'), 1)
        self.assertEqual(results.get('Risk'), 1) # Priority Check
        
    def test_flow_metrics_aggregation(self):
        """Test Flow Velocity and Distribution calculations."""
        print("\n--- Testing Flow Framework: Metrics Aggregation ---")
        now = datetime.now()
        last_week = now - timedelta(days=7)
        
        # Insert 3 Features closed last week
        for _ in range(3):
            self.cursor.execute("INSERT INTO issues (created_at, closed_at, labels, state) VALUES (?, ?, 'feature', 'closed')", 
                                (last_week, now))
        
        # Insert 1 Defect closed last week
        self.cursor.execute("INSERT INTO issues (created_at, closed_at, labels, state) VALUES (?, ?, 'bug', 'closed')", 
                                (last_week, now))
                                
        self.conn.commit()
        
        self.cursor.execute("SELECT flow_velocity, closed_features, closed_defects FROM view_flow_metrics_weekly")
        row = self.cursor.fetchone()
        
        print(f"Metrics Row: {row}")
        
        # row structure based on SELECT: (velocity, features, defects)
        self.assertEqual(row[0], 4, "Should satisfy complete velocity") # velocity
        self.assertEqual(row[1], 3) # features
        self.assertEqual(row[2], 1) # defects

    def test_space_satisfaction_aggregation(self):
        """Test SPACE Framework (Satisfaction) SQL aggregation."""
        print("\n--- Testing SPACE Framework: Satisfaction Logic ---")
        
        today = datetime.now().date()
        
        # Insert Moods: 5, 3, 1 (Avg should be 3.0)
        self.cursor.execute("INSERT INTO satisfaction_records (score, date) VALUES (5, ?)", (today,))
        self.cursor.execute("INSERT INTO satisfaction_records (score, date) VALUES (3, ?)", (today,))
        self.cursor.execute("INSERT INTO satisfaction_records (score, date) VALUES (1, ?)", (today,))
        
        self.conn.commit()
        
        # Run the dashboard query logic
        query = "SELECT AVG(score) as avg_score, COUNT(*) as responses FROM satisfaction_records"
        res = self.cursor.execute(query).fetchone()
        
        print(f"Avg Score: {res[0]}, Responses: {res[1]}")
        
        self.assertEqual(res[1], 3, "Should count 3 responses")

    def test_hotspot_analysis_logic(self):
        """Test Michael Feathers' Hotspot Analysis (Churn vs Complexity)."""
        print("\n--- Testing Code Hotspots: F-C Logic ---")
        
        now = datetime.now()
        day_10_ago = (now - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        day_5_ago = (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
        day_120_ago = (now - timedelta(days=120)).strftime("%Y-%m-%d %H:%M:%S")
        
        file_target = "src/core_logic.py"
        
        # 1. Commit A: ANCIENT History (120 days ago) - Initial Create
        # Should NOT count towards Churn (90d window), but counts towards LOC.
        self.cursor.execute("INSERT INTO commits (id, committed_date) VALUES ('c1', ?)", (day_120_ago,))
        self.cursor.execute("INSERT INTO commit_file_stats (commit_id, file_path, code_added, code_deleted) VALUES ('c1', ?, 100, 0)", (file_target,))
        
        # 2. Commit B: RECENT History (10 days ago) - Feature Add
        # Counts towards Churn AND LOC.
        self.cursor.execute("INSERT INTO commits (id, committed_date) VALUES ('c2', ?)", (day_10_ago,))
        self.cursor.execute("INSERT INTO commit_file_stats (commit_id, file_path, code_added, code_deleted) VALUES ('c2', ?, 50, 0)", (file_target,))
        
        # 3. Commit C: RECENT History (5 days ago) - Refactor (Delete)
        # Counts towards Churn. LOC should reduce.
        self.cursor.execute("INSERT INTO commits (id, committed_date) VALUES ('c3', ?)", (day_5_ago,))
        self.cursor.execute("INSERT INTO commit_file_stats (commit_id, file_path, code_added, code_deleted) VALUES ('c3', ?, 0, 20)", (file_target,))
        
        self.conn.commit()
        
        # Verify View
        self.cursor.execute("SELECT file_path, churn_90d, estimated_loc FROM view_file_hotspots WHERE file_path = ?", (file_target,))
        res = self.cursor.fetchone()
        
        print(f"Hotspot Result: {res}")
        # res layout: (path, churn_90d, loc)
        
        # Churn should be 2 (Commit B and C). Commit A is too old.
        self.assertEqual(res[1], 2, "Churn count logic failed (window filtering?)")
        
        # LOC should be Net Sum: 100 (A) + 50 (B) - 20 (C) = 130
        self.assertEqual(res[2], 130, "Estimated Complexity (LOC) calculation failed")

if __name__ == '__main__':
    unittest.main()
