import requests

api_key = "AIzaSyAhXjWeU6WcmGm1ohSMNMaRkedDG-tpo3c"

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    print("⏳ جاري البحث عن الموديلات المتاحة...")
    response = requests.get(url)
    
    if response.status_code == 200:
        models = response.json().get("models", [])
        print(f"✅ تم إيجاد {len(models)} موديل:")
        for model in models:
            # هطبعلك اسماء الموديلات اللي تقدر تستخدمها
            name = model.get("name", "")
            if "gemini" in name:
                print(f"  - {name}")
    else:
        print(f"❌ فشل! الكود: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"⚠️ خطأ: {e}")