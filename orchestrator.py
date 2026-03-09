import os
import logging
import shutil
from typing import List, Dict, Any
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.docstore.document import Document

logger = logging.getLogger("knowledge_retriever")

class KnowledgeRetriever:
    """نظام استرجاع المعرفة من ملفات PDF باستخدام LangChain و ChromaDB"""
    
    def __init__(self, knowledge_base_dir: str = "knowledge_base", persist_directory: str = "chroma_db"):
        self.knowledge_base_dir = knowledge_base_dir
        self.persist_directory = persist_directory
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # يدعم العربية
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,      # حجم القطعة (حوالي 1000 كلمة)
            chunk_overlap=200,     # تداخل بين القطع لضمان استمرارية السياق
            separators=["\n\n", "\n", ".", " ", ""]
        )
        self.vectorstore = None
        
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
                
                # إضافة معلومات المصدر (اسم الملف) إلى البيانات الوصفية
                for doc in documents:
                    doc.metadata["source"] = pdf_path.name
                    doc.metadata["page"] = doc.metadata.get("page", 0) + 1  # رقم الصفحة
                
                # تقسيم المستند إلى قطع أصغر
                chunks = self.text_splitter.split_documents(documents)
                all_documents.extend(chunks)
                logger.info(f"تم تقسيم {pdf_path.name} إلى {len(chunks)} قطعة")
            except Exception as e:
                logger.error(f"خطأ في معالجة {pdf_path.name}: {e}")
        
        # تخزين القطع في قاعدة بيانات متجهية
        if all_documents:
            # إذا كان المجلد موجوداً، نحذفه أولاً لضمان فهرسة جديدة
            if os.path.exists(self.persist_directory):
                shutil.rmtree(self.persist_directory)
            
            self.vectorstore = Chroma.from_documents(
                documents=all_documents,
                embedding=self.embeddings,
                persist_directory=self.persist_directory
            )
            self.vectorstore.persist()
            logger.info(f"تم فهرسة {len(all_documents)} قطعة معرفة بنجاح")
        else:
            logger.warning("لم يتم استخراج أي نصوص من الملفات")
    
    def load_index(self):
        """تحميل الفهرس الموجود (بدون إعادة الفهرسة)"""
        if os.path.exists(self.persist_directory):
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
            logger.info("تم تحميل الفهرس الموجود")
            return True
        return False
    
    def retrieve(self, query: str, k: int = 5) -> List[Document]:
        """البحث عن أكثر القطع صلة بالسؤال"""
        if not self.vectorstore:
            if not self.load_index():
                logger.error("لا يوجد فهرس معرفة. قم بتشغيل index_pdfs() أولاً")
                return []
        
        # استخدام MMR (Maximum Marginal Relevance) للحصول على نتائج متنوعة
        docs = self.vectorstore.max_marginal_relevance_search(query, k=k, fetch_k=20)
        return docs
    
    def format_context(self, docs: List[Document]) -> str:
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

# إنشاء كائن عام للاستخدام في التطبيق
retriever = KnowledgeRetriever()

# إذا كان هناك مجلد معرفة، حاول تحميل الفهرس، وإلا فهرسة الملفات
if os.path.exists("knowledge_base"):
    if not retriever.load_index():
        print("🟡 جاري فهرسة ملفات PDF لأول مرة (قد يستغرق بضع دقائق)...")
        retriever.index_pdfs()
        print("🟢 تمت الفهرسة بنجاح")
else:
    print("🔴 مجلد knowledge_base غير موجود. أنشئه وأضف ملفات PDF")
