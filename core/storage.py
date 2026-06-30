"""
持久化存储模块 — 使用 SQLite 保存面试数据

核心功能：
1. 面试会话管理（创建、查询、结束会话）
2. 对话历史存储（保存用户和 AI 消息）
3. 评分记录管理（多维度评分存储与查询）
4. 简历信息存储（文本内容和文件路径）

数据库表：
- interview_sessions  : 面试会话主表
- chat_history        : 对话历史表
- evaluations         : 评分记录表
- resumes             : 简历记录表
"""
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import config


class InterviewStorage:
    """
    面试数据持久化存储

    使用 SQLite 作为底层存储，无需额外安装数据库服务。
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(config.DB_PATH)
        self._init_database()

    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 面试会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interview_sessions (
                session_id    TEXT PRIMARY KEY,
                candidate_name TEXT DEFAULT '',
                position      TEXT DEFAULT '',
                interview_style TEXT DEFAULT 'default',
                start_time    TEXT,
                end_time      TEXT,
                status        TEXT DEFAULT 'active',
                metadata      TEXT DEFAULT '{}'
            )
        """)

        # 对话历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT,
                role        TEXT,
                content     TEXT,
                timestamp   TEXT,
                FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id)
            )
        """)

        # 评分记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT,
                dimension   TEXT,
                score       INTEGER,
                comment     TEXT,
                timestamp   TEXT,
                FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id)
            )
        """)

        # 简历表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resumes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT,
                file_name   TEXT,
                file_path   TEXT,
                resume_text TEXT DEFAULT '',
                upload_time TEXT,
                FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id)
            )
        """)

        conn.commit()
        conn.close()

    # ══════════════════════════════════════════════
    # 会话管理
    # ══════════════════════════════════════════════

    def create_session(
        self,
        session_id: str,
        candidate_name: str = "",
        position: str = "",
        interview_style: str = "default",
        metadata: Optional[Dict] = None,
    ) -> bool:
        """创建新的面试会话"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO interview_sessions
                (session_id, candidate_name, position, interview_style, start_time, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, candidate_name, position, interview_style,
                datetime.now().isoformat(), "active",
                json.dumps(metadata or {}, ensure_ascii=False),
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[storage] 创建会话失败: {e}")
            return False

    def end_session(self, session_id: str) -> bool:
        """结束面试会话"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE interview_sessions
                SET end_time = ?, status = 'completed'
                WHERE session_id = ?
            """, (datetime.now().isoformat(), session_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[storage] 结束会话失败: {e}")
            return False

    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """获取会话详细信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT session_id, candidate_name, position, interview_style,
                       start_time, end_time, status, metadata
                FROM interview_sessions WHERE session_id = ?
            """, (session_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    "session_id": row[0],
                    "candidate_name": row[1],
                    "position": row[2],
                    "interview_style": row[3],
                    "start_time": row[4],
                    "end_time": row[5],
                    "status": row[6],
                    "metadata": json.loads(row[7]) if row[7] else {},
                }
            return None
        except Exception as e:
            print(f"[storage] 获取会话信息失败: {e}")
            return None

    def list_sessions(self, limit: int = 50) -> List[Dict]:
        """列出所有面试会话（最新在前）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT session_id, candidate_name, position, interview_style,
                       start_time, end_time, status
                FROM interview_sessions
                ORDER BY start_time DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            conn.close()
            return [
                {
                    "session_id": row[0], "candidate_name": row[1],
                    "position": row[2], "interview_style": row[3],
                    "start_time": row[4], "end_time": row[5], "status": row[6],
                }
                for row in rows
            ]
        except Exception as e:
            print(f"[storage] 列出会话失败: {e}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """删除会话及关联数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for table in ("chat_history", "evaluations", "resumes"):
                cursor.execute(f"DELETE FROM {table} WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM interview_sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[storage] 删除会话失败: {e}")
            return False

    # ══════════════════════════════════════════════
    # 对话历史
    # ══════════════════════════════════════════════

    def save_message(self, session_id: str, role: str, content: str) -> bool:
        """保存一条对话消息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chat_history (session_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
            """, (session_id, role, content, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[storage] 保存消息失败: {e}")
            return False

    def get_session_history(self, session_id: str) -> List[Dict]:
        """获取会话的完整对话历史"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT role, content, timestamp
                FROM chat_history WHERE session_id = ?
                ORDER BY id ASC
            """, (session_id,))
            rows = cursor.fetchall()
            conn.close()
            return [
                {"role": row[0], "content": row[1], "timestamp": row[2]}
                for row in rows
            ]
        except Exception as e:
            print(f"[storage] 获取历史失败: {e}")
            return []

    # ══════════════════════════════════════════════
    # 评分
    # ══════════════════════════════════════════════

    def save_evaluation(
        self, session_id: str, dimension: str, score: int, comment: str = ""
    ) -> bool:
        """保存一条评分记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO evaluations (session_id, dimension, score, comment, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, dimension, score, comment, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[storage] 保存评分失败: {e}")
            return False

    def get_session_evaluations(self, session_id: str) -> List[Dict]:
        """获取会话的所有评分记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT dimension, score, comment
                FROM evaluations WHERE session_id = ?
            """, (session_id,))
            rows = cursor.fetchall()
            conn.close()
            return [
                {"dimension": row[0], "score": row[1], "comment": row[2]}
                for row in rows
            ]
        except Exception as e:
            print(f"[storage] 获取评分失败: {e}")
            return []

    def get_session_statistics(self, session_id: str) -> Dict:
        """获取会话统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM chat_history
                WHERE session_id = ? AND role = 'user'
            """, (session_id,))
            turn_count = cursor.fetchone()[0]

            cursor.execute("""
                SELECT dimension, score, comment
                FROM evaluations WHERE session_id = ?
            """, (session_id,))
            evaluations = [
                {"dimension": row[0], "score": row[1], "comment": row[2]}
                for row in cursor.fetchall()
            ]
            conn.close()

            avg = sum(e["score"] for e in evaluations) / len(evaluations) if evaluations else 0
            return {
                "turn_count": turn_count,
                "evaluations": evaluations,
                "avg_score": round(avg, 2),
            }
        except Exception as e:
            print(f"[storage] 获取统计失败: {e}")
            return {"turn_count": 0, "evaluations": [], "avg_score": 0}

    # ══════════════════════════════════════════════
    # 简历
    # ══════════════════════════════════════════════

    def save_resume(
        self, session_id: str, file_name: str,
        file_path: str, resume_text: str = "",
    ) -> bool:
        """保存简历信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO resumes (session_id, file_name, file_path, resume_text, upload_time)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, file_name, file_path, resume_text, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[storage] 保存简历失败: {e}")
            return False

    def get_session_resume(self, session_id: str) -> Optional[Dict]:
        """获取会话最新的简历"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT file_name, file_path, resume_text, upload_time
                FROM resumes WHERE session_id = ?
                ORDER BY id DESC LIMIT 1
            """, (session_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    "file_name": row[0], "file_path": row[1],
                    "resume_text": row[2], "upload_time": row[3],
                }
            return None
        except Exception as e:
            print(f"[storage] 获取简历失败: {e}")
            return None

    def list_resumes(self, limit: int = 20) -> List[Dict]:
        """列出所有简历"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.id, r.session_id, r.file_name, r.upload_time,
                       s.candidate_name, s.position
                FROM resumes r
                LEFT JOIN interview_sessions s ON r.session_id = s.session_id
                ORDER BY r.upload_time DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            conn.close()
            return [
                {
                    "id": row[0], "session_id": row[1], "file_name": row[2],
                    "upload_time": row[3], "candidate_name": row[4], "position": row[5],
                }
                for row in rows
            ]
        except Exception as e:
            print(f"[storage] 列出简历失败: {e}")
            return []
