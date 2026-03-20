#!/usr/bin/env python3
"""
KnowledgeBase - 向量数据库知识库 v2.0
使用ChromaDB存储和检索学习到的知识
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("⚠️ ChromaDB未安装，使用JSON回退模式")

WORKSPACE = Path("/Users/magicuncle/.openclaw/workspace")
DATA_DIR = WORKSPACE / "agents" / "architect" / "data"
VECTOR_DIR = DATA_DIR / "vector_db"


class KnowledgeBase:
    """向量数据库知识库"""
    
    def __init__(self, collection_name: str = "architect_knowledge"):
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self.json_fallback = {}
        
        if CHROMA_AVAILABLE:
            self._init_chroma()
        else:
            self._init_json_fallback()
    
    def _init_chroma(self):
        """初始化ChromaDB"""
        try:
            VECTOR_DIR.mkdir(parents=True, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=str(VECTOR_DIR),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # 获取或创建集合
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Architect学习知识库"}
            )
            
            print(f"✅ ChromaDB初始化成功: {VECTOR_DIR}")
            
        except Exception as e:
            print(f"⚠️ ChromaDB初始化失败: {e}，使用JSON回退")
            self._init_json_fallback()
    
    def _init_json_fallback(self):
        """初始化JSON回退模式"""
        self.json_file = DATA_DIR / "knowledge_fallback.json"
        if self.json_file.exists():
            with open(self.json_file, 'r', encoding='utf-8') as f:
                self.json_fallback = json.load(f)
        print(f"✅ JSON回退模式: {self.json_file}")
    
    def add_knowledge(self, 
                      content: str, 
                      metadata: Dict[str, Any],
                      embedding: Optional[List[float]] = None) -> str:
        """添加知识条目"""
        
        # 生成唯一ID
        doc_id = hashlib.md5(
            f"{content}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        if self.collection and CHROMA_AVAILABLE:
            # 使用ChromaDB
            try:
                self.collection.add(
                    ids=[doc_id],
                    documents=[content],
                    metadatas=[{
                        **metadata,
                        "added_at": datetime.now().isoformat()
                    }],
                    embeddings=[embedding] if embedding else None
                )
                return doc_id
            except Exception as e:
                print(f"⚠️ ChromaDB添加失败: {e}")
        
        # JSON回退
        self.json_fallback[doc_id] = {
            "content": content,
            "metadata": {
                **metadata,
                "added_at": datetime.now().isoformat()
            }
        }
        self._save_json_fallback()
        return doc_id
    
    def search_similar(self, 
                       query: str, 
                       n_results: int = 5,
                       filters: Optional[Dict] = None) -> List[Dict]:
        """相似性搜索"""
        
        if self.collection and CHROMA_AVAILABLE:
            try:
                where_clause = filters if filters else None
                
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where=where_clause
                )
                
                # 格式化结果
                formatted = []
                for i in range(len(results['ids'][0])):
                    formatted.append({
                        "id": results['ids'][0][i],
                        "content": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i] if 'distances' in results else None
                    })
                
                return formatted
                
            except Exception as e:
                print(f"⚠️ ChromaDB搜索失败: {e}")
        
        # JSON回退（简单关键词匹配）
        return self._json_search(query, n_results)
    
    def _json_search(self, query: str, n_results: int) -> List[Dict]:
        """JSON模式的简单搜索"""
        query_terms = query.lower().split()
        scores = []
        
        for doc_id, data in self.json_fallback.items():
            content = data["content"].lower()
            score = sum(1 for term in query_terms if term in content)
            if score > 0:
                scores.append((score, doc_id, data))
        
        # 排序并返回前N个
        scores.sort(reverse=True)
        results = []
        
        for score, doc_id, data in scores[:n_results]:
            results.append({
                "id": doc_id,
                "content": data["content"],
                "metadata": data["metadata"],
                "distance": 1.0 / (score + 1)  # 模拟距离
            })
        
        return results
    
    def get_stats(self) -> Dict:
        """获取知识库统计"""
        
        if self.collection and CHROMA_AVAILABLE:
            try:
                count = self.collection.count()
                return {
                    "total_documents": count,
                    "storage_type": "chroma",
                    "storage_path": str(VECTOR_DIR)
                }
            except Exception as e:
                print(f"⚠️ ChromaDB统计失败: {e}")
        
        return {
            "total_documents": len(self.json_fallback),
            "storage_type": "json_fallback",
            "storage_path": str(self.json_file)
        }
    
    def _save_json_fallback(self):
        """保存JSON回退数据"""
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(self.json_fallback, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # 简单测试
    kb = KnowledgeBase()
    print(f"\nKnowledgeBase initialized: {kb.get_stats()}")
