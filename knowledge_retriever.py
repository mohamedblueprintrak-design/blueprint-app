import os
import logging
from typing import List, Dict, Any
from pathlib import Path

# استيراد مكتبات التعامل مع PDF والتقسيم
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# إعداد التسجيل
logger = logging.getLogger("knowledge_retriever")

class KnowledgeRetriever:
    """نظام استرجاع المعرفة من ملفات PDF"""
    
    def __init__(self, knowledge_base_dir: str = "knowledge_base", persist_directory: str = "chroma_db"):
        self.knowledge_base_dir = knowledge_base_dir
        self.persist_directory = persist_directory
        self.vectorstore = None
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # نموذج يدعم العربية
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,      # حجم القطعة (حوالي 500 كلمة)
            chunk_overlap=50,    # تداخل بسيط بين القطع للحفاظ على السياق
            separators=["\n\n", "\n", ".", " ", ""]
        )
        
    def index_pdfs(self):
        """قراءة جميع ملفات PDF في المجلد وفهرستها"""
        pdf_files = list(Path(self.knowledge_base_dir).glob("*.pdf"))
        if not pdf_files:
            logger.warning("لا توجد ملفات PDF في المجلد %s", self.knowledge_base_dir)
            return
        
        all_documents = []
        for pdf_path in pdf_files:
            logger.info(f"جاري معالجة الملف: {pdf_path.name}")
            loader = PyPDFLoader(str(pdf_path))
            documents = loader.load()
            
            # إضافة معلومات المصدر (اسم الملف) إلى البيانات الوصفية لكل صفحة
            for doc in documents:
                doc.metadata["source_file"] = pdf_path.name
                doc.metadata["source_page"] = doc.metadata.get("page", 0) + 1  # رقم الصفحة
            
            # تقسيم المستند إلى قطع أصغر
            chunks = self.text_splitter.split_documents(documents)
            all_documents.extend(chunks)
            logger.info(f"تم تقسيم {pdf_path.name} إلى {len(chunks)} قطعة")
        
        # تخزين القطع في قاعدة بيانات متجهية
        if all_documents:
            self.vectorstore = Chroma.from_documents(
                documents=all_documents,
                embedding=self.embeddings,
                persist_directory=self.persist_directory
            )
            self.vectorstore.persist()
            logger.info(f"تم فهرسة {len(all_documents)} قطعة معرفة")
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
    
    def retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """البحث عن أكثر القطع صلة بالسؤال"""
        if not self.vectorstore:
            if not self.load_index():
                logger.error("لا يوجد فهرس معرفة. قم بتشغيل index_pdfs() أولاً")
                return []
        
        results = self.vectorstore.similarity_search_with_score(query, k=k)
        retrieved = []
        for doc, score in results:
            retrieved.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source_file", "غير معروف"),
                "page": doc.metadata.get("source_page", "غير معروف"),
                "score": score
            })
        return retrieved
    
    def format_context(self, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """تنسيق القطع المسترجعة لتكون سياقاً مقروءاً"""
        if not retrieved_chunks:
            return ""
        
        context = "المعلومات التالية مأخوذة من المراجع الهندسية:\n\n"
        for i, chunk in enumerate(retrieved_chunks, 1):
            context += f"[{i}] من {chunk['source']} (صفحة {chunk['page']}):\n"
            context += chunk['content'].strip() + "\n\n"
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