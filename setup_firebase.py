import os

def create_config_file():
    print("أدخل بيانات Firebase الخاصة بك:")
    api_key = input("أدخل API Key: ")
    project_id = input("أدخل Project ID: ")
    
    # إنشاء محتوى ملف التكوين
    config_content = f'''FIREBASE_CONFIG = {{
    "apiKey": "{api_key}",
    "authDomain": "{project_id}.firebaseapp.com",
    "databaseURL": "https://{project_id}-default-rtdb.firebaseio.com",
    "storageBucket": "{project_id}.appspot.com"
}}'''
    
    # كتابة الملف
    with open('config.py', 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    # تحديث ملف mobile_controller.html
    with open('mobile_controller.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # استبدال بيانات Firebase في ملف HTML
    updated_content = content.replace(
        '"YOUR_API_KEY"', f'"{api_key}"'
    ).replace(
        'YOUR_PROJECT_ID', project_id
    )
    
    with open('mobile_controller.html', 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print("\nتم إنشاء ملفات التكوين بنجاح!")
    print("يمكنك الآن تشغيل التطبيق باستخدام الأمر: python windows_controller.py")

if __name__ == "__main__":
    create_config_file()
