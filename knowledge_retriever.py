import os
import logging
import shutil
from pathlib import Path
from typing import List, Optional

# استخدام langchain_community
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

logger = logging.getLogger("knowledge_retriever")

class KnowledgeRetriever:
    """نظام استرجاع المعرفة من ملفات PDF باستخدام LangChain و ChromaDB"""
    
    def __init__(self, knowledge_base_dir: str = "knowledge_base", persist_directory: str = "chroma_db"):
        self.knowledge_base_dir = knowledge_base_dir
        self.persist_directory = persist_directory
        self._embeddings = None
        self._text_splitter = None
        self._vectorstore = None
    
    @property
    def embeddings(self):
        """تحميل نموذج التضمين عند الطلب فقط (Lazy Loading)"""
        if self._embeddings is None:
            print("🟡 جاري تحميل نموذج التضمين لأول مرة (قد يستغرق 30-60 ثانية)...")
            self._embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            print("🟢 تم تحميل نموذج التضمين بنجاح")
        return self._embeddings
    
    @property
    def text_splitter(self):
        """إعداد تقسيم النصوص"""
        if self._text_splitter is None:
            self._text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ".", " ", ""]
            )
        return self._text_splitter
    
    def index_pdfs(self):
        """فهرسة جميع ملفات PDF في مجلد knowledge_base"""
        pdf_files = list(Path(self.knowledge_base_dir).glob("*.pdf"))
        if not pdf_files:
            logger.warning("لا توجد ملفات PDF في المجلد %s", self.knowledge_base_dir)
            return
        
        all_documents = []
        for pdf_path in pdf_files:
            logger.info(f"جاري معالجة الملف: {pdf_path.name}")
            try:
                loader = PyPDFLoader(str(pdf_path))
                documents = loader.load()
                
                for doc in documents:
                    doc.metadata["source"] = pdf_path.name
                    doc.metadata["page"] = doc.metadata.get("page", 0) + 1
                
                chunks = self.text_splitter.split_documents(documents)
                all_documents.extend(chunks)
                logger.info(f"تم تقسيم {pdf_path.name} إلى {len(chunks)} قطعة")
            except Exception as e:
                logger.error(f"خطأ في معالجة {pdf_path.name}: {e}")
        
        if all_documents:
            if os.path.exists(self.persist_directory):
                shutil.rmtree(self.persist_directory)
            
            self._vectorstore = Chroma.from_documents(
                documents=all_documents,
                embedding=self.embeddings,
                persist_directory=self.persist_directory
            )
            # persist() تمت إزالتها في الإصدارات الجديدة من Chroma، لكن نتركها للتوافق
            if hasattr(self._vectorstore, 'persist'):
                self._vectorstore.persist()
            logger.info(f"تم فهرسة {len(all_documents)} قطعة معرفة بنجاح")
        else:
            logger.warning("لم يتم استخراج أي نصوص من الملفات")
    
    def load_index(self):
        """تحميل الفهرس الموجود (بدون إعادة الفهرسة)"""
        if os.path.exists(self.persist_directory):
            self._vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
            logger.info("تم تحميل الفهرس الموجود")
            return True
        return False
    
    def retrieve(self, query: str, k: int = 5):
        """البحث عن أكثر القطع صلة بالسؤال"""
        if not self._vectorstore:
            if not self.load_index():
                logger.error("لا يوجد فهرس معرفة. قم بتشغيل index_pdfs() أولاً")
                return []
        
        docs = self._vectorstore.similarity_search(query, k=k)
        return docs
    
    def format_context(self, docs) -> str:
        """تنسيق القطع المسترجعة لتكون سياقاً مقروءاً"""
        if not docs:
            return ""
        
        context = "المعلومات التالية مأخوذة من المراجع الهندسية:\n\n"
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "غير معروف")
            page = doc.metadata.get("page", "غير معروف")
            context += f"[{i}] من {source} (صفحة {page}):\n"
            context += doc.page_content.strip() + "\n\n"
        return context


# --- Lazy Loading للكائن العام ---
_retriever_instance = None

def get_retriever():
    """إرجاع كائن KnowledgeRetriever (يتم تحميله عند الطلب)"""
    global _retriever_instance
    if _retriever_instance is None:
        print("🟡 تهيئة نظام استرجاع المعرفة...")
        _retriever_instance = KnowledgeRetriever()
        # محاولة تحميل الفهرس الموجود فقط
        # استخدام self.persist_directory لتجنب أخطاء المسار
        if os.path.exists(_retriever_instance.persist_directory):
            _retriever_instance.load_index()
        print("🟢 تم تهيئة نظام استرجاع المعرفة")
    return _retriever_instance

# ⚠️ تم حذف السطر التالي عمداً لأنه كان يسبب تعطل السيرفر
# retriever = get_retriever()
# بدلاً من ذلك، استدعِ get_retriever() من داخل دوال الـ API فقط عند الحاجة.
