الرجاء إضافة ميزة "مصحح الكتابة الأكاديمية" (Academic Writing Reviewer) إلى بوت التيليجرام باستخدام مكتبة groq.

المطلوب تنفيذه بدقة داخل الكود:

تحديث واجهة البوت: أضف زراً جديداً في القائمة الرئيسية للبوت باسم 📝 "مصحح الكتابة الأكاديمية" (إلى جانب زر المساعد اللغوي).

فصل حالة المحادثة (State Management): أنشئ حالة جديدة (State) خاصة بهذا القسم (مثلاً ACADEMIC_WRITING_STATE) لكي لا تتداخل مع قسم المساعد اللغوي العادي. أضف زر 🔙 "العودة للقائمة الرئيسية" داخل هذه الحالة.

توجيه الذكاء الاصطناعي (System Prompt الأكاديمي): استخدم نموذج llama3-70b-8192 (لأنه الأقوى في التحليل المعقد) وقم بضبط system_prompt الخاص بهذه الحالة ليكون كالتالي تحديداً:
*"You are an expert University Professor of English Language and Literature at Fluence English Academy. Your task is to evaluate and proofread academic writing, essays, and literature analyses submitted by university students.
Strictly focus on:

Academic tone and formal vocabulary.

Correct usage of transition signals and coherence.

Grammatical accuracy and sentence variety.

If the text discusses literature, assume the context is World Literature (especially Poetry and Drama).
Provide your feedback in this format:

📊 Overall Score (Out of 10)

🧐 Critique & Errors (Point out specific mistakes)

✨ Polished Academic Version (Rewrite the text professionally)."*

معالجة النصوص: عندما يرسل الطالب نصاً أو مقالاً في هذه الحالة، يتم إرساله إلى Groq بهذا التوجيه الصارم، ثم يُرسل الرد المنظم للطالب.

التعامل مع الأخطاء: استخدم try-except للتعامل مع النصوص الطويلة جداً أو تأخر الاستجابة، مع إرسال رسالة توضيحية للطالب في حال حدوث خطأ.

الرجاء كتابة الكود اللازم لتطبيق هذه الميزة، ثم عمل Commit و Push إلى GitHub ليتم تحديث البوت عبر Render.
