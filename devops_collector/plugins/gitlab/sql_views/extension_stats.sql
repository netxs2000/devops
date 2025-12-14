-- Extension Stats View
-- Reconstructs the current codebase composition by aggregating historical diffs.
-- 
-- Logic:
-- 1. Aggregates additions/deletions per file path.
-- 2. "Existing Files" are those where total_lines > 0.
-- 3. Extracts extension from file_path.
-- 4. Calculates usage metrics.
-- 5. Zeroes out line counts for known Asset/Binary types.

CREATE OR REPLACE VIEW view_extension_stats AS
WITH file_snapshot AS (
    SELECT
        cfs.project_id,
        cfs.file_path,
        SUM(cfs.code_added + cfs.blank_added + cfs.comment_added) - 
        SUM(cfs.code_deleted + cfs.blank_deleted + cfs.comment_deleted) as current_lines
    FROM commit_file_stats cfs
    GROUP BY cfs.project_id, cfs.file_path
    HAVING (SUM(cfs.code_added + cfs.blank_added + cfs.comment_added) - 
            SUM(cfs.code_deleted + cfs.blank_deleted + cfs.comment_deleted)) > 0
),
extension_data AS (
    SELECT
        project_id,
        current_lines,
        CASE
            WHEN position('.' in RIGHT(file_path, length(file_path) - position('/' in REVERSE(file_path)))) > 0 THEN
               substring(file_path from '\.([^\.]+)$')
            ELSE 'no_extension'
        END as extension
    FROM file_snapshot
)
SELECT
    ed.project_id,
    p.name as project_name,
    ed.extension,
    COUNT(*) as file_count,
    
    -- Zero out lines for assets
    SUM(
        CASE 
            WHEN ed.extension IN ('png', 'jpg', 'jpeg', 'gif', 'ico', 'svg', 'webp', 'bmp', 'tif', 'tiff', 'psd',
                                  'mp3', 'mp4', 'wav', 'avi', 'mov', 'flv', 'wmv', 'm4a', 'aac', 'ogg',
                                  'zip', 'tar', 'gz', '7z', 'rar', 'iso', 'dmg',
                                  'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                                  'exe', 'dll', 'so', 'dylib', 'class', 'jar', 'war', 'ear', 'apk', 'ipa') 
            THEN 0
            ELSE ed.current_lines
        END
    ) as total_lines,
    
    ROUND(AVG(
        CASE 
            WHEN ed.extension IN ('png', 'jpg', 'jpeg', 'gif', 'ico', 'svg', 'webp', 'bmp', 'tif', 'tiff', 'psd',
                                  'mp3', 'mp4', 'wav', 'avi', 'mov', 'flv', 'wmv', 'm4a', 'aac', 'ogg',
                                  'zip', 'tar', 'gz', '7z', 'rar', 'iso', 'dmg',
                                  'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                                  'exe', 'dll', 'so', 'dylib', 'class', 'jar', 'war', 'ear', 'apk', 'ipa') 
            THEN 0
            ELSE ed.current_lines
        END
    ), 2) as avg_lines_per_file
    
FROM extension_data ed
JOIN projects p ON ed.project_id = p.id
GROUP BY ed.project_id, p.name, ed.extension
ORDER BY total_lines DESC;
