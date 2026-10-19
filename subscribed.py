"""The /subscribed/ celebration page shown after a newsletter confirmation (noindex, not in menus or sitemap.xml)."""
import json
from html import escape as E

KEYS = ("title", "desc", "h1", "lead", "week_h", "p1", "p2", "p3", "p4", "s_issues", "s_langs", "s_stories",
        "next_h", "d", "h", "m", "s", "read", "tg", "x", "rss", "home", "again", "unsub")

S = {
"en": dict(title="Welcome aboard", desc="Your Nordic Crypto newsletter subscription is confirmed.", h1="Welcome aboard!",
    lead="Your subscription is confirmed. A new issue lands in your inbox every Monday morning.", week_h="Every week you get",
    p1="The week's most important crypto news from the Nordics", p2="Regulation and MiCA, explained in plain words",
    p3="Upcoming events across the Nordics", p4="A short video round-up of the week",
    s_issues="issues so far", s_langs="languages", s_stories="stories in the latest issue", next_h="Next issue in",
    d="days", h="hours", m="min", s="sec", read="Read the latest issue", tg="Chat on Telegram", x="Follow on X",
    rss="Add the RSS feed", home="Go to the front page", again="Celebrate again",
    unsub="You can unsubscribe with the link at the bottom of every email."),
"nn": dict(title="Velkomen inn", desc="Abonnementet ditt på nyheitsbrevet frå Nordic Crypto er stadfesta.", h1="Velkomen inn!",
    lead="Abonnementet ditt er stadfesta. Ei ny utgåve kjem i innboksen din kvar måndag morgon.", week_h="Kvar veke får du",
    p1="Dei viktigaste kryptonyheitene frå Norden denne veka", p2="Regulering og MiCA, forklart på godt norsk",
    p3="Arrangement som kjem i Norden", p4="Ei kort videooppsummering av veka",
    s_issues="utgåver så langt", s_langs="språk", s_stories="saker i siste utgåve", next_h="Neste utgåve om",
    d="dagar", h="timar", m="min", s="sek", read="Les siste utgåve", tg="Prat med oss på Telegram", x="Følg oss på X",
    rss="Legg til RSS-feeden", home="Til framsida", again="Feir ein gong til",
    unsub="Du kan melde deg av med lenkja nedst i kvar e-post."),
"nb": dict(title="Velkommen inn", desc="Abonnementet ditt på nyhetsbrevet fra Nordic Crypto er bekreftet.", h1="Velkommen inn!",
    lead="Abonnementet ditt er bekreftet. En ny utgave lander i innboksen din hver mandag morgen.", week_h="Hver uke får du",
    p1="Ukens viktigste kryptonyheter fra Norden", p2="Regulering og MiCA, forklart på godt norsk",
    p3="Kommende arrangementer i Norden", p4="En kort videooppsummering av uken",
    s_issues="utgaver så langt", s_langs="språk", s_stories="saker i siste utgave", next_h="Neste utgave om",
    d="dager", h="timer", m="min", s="sek", read="Les siste utgave", tg="Prat med oss på Telegram", x="Følg oss på X",
    rss="Legg til RSS-feeden", home="Til forsiden", again="Feire en gang til",
    unsub="Du kan melde deg av med lenken nederst i hver e-post."),
"sv": dict(title="Välkommen in", desc="Din prenumeration på nyhetsbrevet från Nordic Crypto är bekräftad.", h1="Välkommen in!",
    lead="Din prenumeration är bekräftad. Ett nytt nummer landar i din inkorg varje måndagsmorgon.", week_h="Varje vecka får du",
    p1="Veckans viktigaste kryptonyheter från Norden", p2="Reglering och MiCA, förklarat på enkel svenska",
    p3="Kommande evenemang i Norden", p4="En kort videosammanfattning av veckan",
    s_issues="nummer hittills", s_langs="språk", s_stories="artiklar i senaste numret", next_h="Nästa nummer om",
    d="dagar", h="timmar", m="min", s="sek", read="Läs senaste numret", tg="Chatta på Telegram", x="Följ oss på X",
    rss="Lägg till RSS-flödet", home="Till startsidan", again="Fira igen",
    unsub="Du kan avsluta prenumerationen med länken längst ner i varje mejl."),
"da": dict(title="Velkommen indenfor", desc="Dit abonnement på nyhedsbrevet fra Nordic Crypto er bekræftet.", h1="Velkommen indenfor!",
    lead="Dit abonnement er bekræftet. Et nyt nummer lander i din indbakke hver mandag morgen.", week_h="Hver uge får du",
    p1="Ugens vigtigste kryptonyheder fra Norden", p2="Regulering og MiCA, forklaret i et klart sprog",
    p3="Kommende arrangementer i Norden", p4="En kort videoopsummering af ugen",
    s_issues="numre indtil nu", s_langs="sprog", s_stories="artikler i seneste nummer", next_h="Næste nummer om",
    d="dage", h="timer", m="min", s="sek", read="Læs seneste nummer", tg="Chat på Telegram", x="Følg os på X",
    rss="Tilføj RSS-feedet", home="Til forsiden", again="Fejr det igen",
    unsub="Du kan afmelde dig med linket nederst i hver e-mail."),
"fi": dict(title="Tervetuloa mukaan", desc="Nordic Crypton uutiskirjeen tilauksesi on vahvistettu.", h1="Tervetuloa mukaan!",
    lead="Tilauksesi on vahvistettu. Uusi numero saapuu sähköpostiisi joka maanantaiaamu.", week_h="Joka viikko saat",
    p1="Viikon tärkeimmät kryptouutiset Pohjoismaista", p2="Sääntely ja MiCA selkeästi selitettynä",
    p3="Tulevat tapahtumat Pohjoismaissa", p4="Lyhyt videokooste viikosta",
    s_issues="numeroa tähän mennessä", s_langs="kieltä", s_stories="juttua uusimmassa numerossa", next_h="Seuraava numero",
    d="päivää", h="tuntia", m="min", s="s", read="Lue uusin numero", tg="Keskustele Telegramissa", x="Seuraa X:ssä",
    rss="Lisää RSS-syöte", home="Etusivulle", again="Juhli uudestaan",
    unsub="Voit perua tilauksen jokaisen viestin lopussa olevasta linkistä."),
"is": dict(title="Velkomin um borð", desc="Áskrift þín að fréttabréfi Nordic Crypto er staðfest.", h1="Velkomin um borð!",
    lead="Áskriftin þín er staðfest. Nýtt tölublað berst í pósthólfið þitt alla mánudagsmorgna.", week_h="Í hverri viku færðu",
    p1="Mikilvægustu rafmyntafréttir vikunnar frá Norðurlöndum", p2="Regluverk og MiCA, útskýrt á mannamáli",
    p3="Viðburði fram undan á Norðurlöndum", p4="Stutta myndbandssamantekt vikunnar",
    s_issues="tölublöð hingað til", s_langs="tungumál", s_stories="fréttir í nýjasta tölublaði", next_h="Næsta tölublað eftir",
    d="daga", h="klst.", m="mín.", s="sek.", read="Lesa nýjasta tölublaðið", tg="Spjalla á Telegram", x="Fylgja á X",
    rss="Bæta við RSS-straumnum", home="Á forsíðuna", again="Fagna aftur",
    unsub="Þú getur sagt upp áskriftinni með hlekknum neðst í hverjum pósti."),
"zh": dict(title="欢迎加入", desc="您的 Nordic Crypto 新闻简报订阅已确认。", h1="欢迎加入！",
    lead="您的订阅已确认。每周一早上，新一期简报都会送达您的收件箱。", week_h="每周您将收到",
    p1="本周北欧最重要的加密货币新闻", p2="用浅显的语言解读监管与 MiCA", p3="北欧即将举行的活动", p4="一段简短的本周视频回顾",
    s_issues="期已发布", s_langs="种语言", s_stories="篇报道（最新一期）", next_h="距离下一期还有",
    d="天", h="小时", m="分", s="秒", read="阅读最新一期", tg="在 Telegram 上聊天", x="在 X 上关注我们",
    rss="添加 RSS 订阅", home="返回首页", again="再庆祝一次", unsub="每封邮件底部都有退订链接。"),
"hi": dict(title="स्वागत है", desc="Nordic Crypto न्यूज़लेटर की आपकी सदस्यता की पुष्टि हो गई है।", h1="आपका स्वागत है!",
    lead="आपकी सदस्यता की पुष्टि हो गई है। हर सोमवार सुबह एक नया अंक आपके इनबॉक्स में आएगा।", week_h="हर हफ़्ते आपको मिलेगा",
    p1="नॉर्डिक देशों से हफ़्ते की सबसे अहम क्रिप्टो ख़बरें", p2="नियमन और MiCA, आसान शब्दों में",
    p3="नॉर्डिक देशों में आने वाले कार्यक्रम", p4="हफ़्ते का एक छोटा वीडियो सारांश",
    s_issues="अंक अब तक", s_langs="भाषाएँ", s_stories="ख़बरें नवीनतम अंक में", next_h="अगला अंक आने में",
    d="दिन", h="घंटे", m="मिनट", s="सेकंड", read="नवीनतम अंक पढ़ें", tg="Telegram पर चैट करें", x="X पर फ़ॉलो करें",
    rss="RSS फ़ीड जोड़ें", home="मुखपृष्ठ पर जाएँ", again="फिर से जश्न मनाएँ", unsub="हर ईमेल के नीचे दिए लिंक से आप सदस्यता छोड़ सकते हैं।"),
"es": dict(title="Bienvenido a bordo", desc="Tu suscripción al boletín de Nordic Crypto está confirmada.", h1="¡Bienvenido a bordo!",
    lead="Tu suscripción está confirmada. Cada lunes por la mañana llegará un nuevo número a tu bandeja de entrada.", week_h="Cada semana recibirás",
    p1="Las noticias cripto más importantes de los países nórdicos", p2="Regulación y MiCA, explicadas con claridad",
    p3="Próximos eventos en los países nórdicos", p4="Un breve resumen de la semana en vídeo",
    s_issues="números hasta ahora", s_langs="idiomas", s_stories="noticias en el último número", next_h="Próximo número en",
    d="días", h="horas", m="min", s="s", read="Leer el último número", tg="Chatea en Telegram", x="Síguenos en X",
    rss="Añadir el feed RSS", home="Ir a la portada", again="Celebrar otra vez",
    unsub="Puedes darte de baja con el enlace al final de cada correo."),
"fr": dict(title="Bienvenue à bord", desc="Votre abonnement à la lettre d’information de Nordic Crypto est confirmé.", h1="Bienvenue à bord !",
    lead="Votre abonnement est confirmé. Un nouveau numéro arrive dans votre boîte chaque lundi matin.", week_h="Chaque semaine, vous recevez",
    p1="L’essentiel de l’actualité crypto des pays nordiques", p2="La réglementation et MiCA, expliquées simplement",
    p3="Les prochains événements dans les pays nordiques", p4="Un court récapitulatif vidéo de la semaine",
    s_issues="numéros parus", s_langs="langues", s_stories="articles dans le dernier numéro", next_h="Prochain numéro dans",
    d="jours", h="heures", m="min", s="s", read="Lire le dernier numéro", tg="Discuter sur Telegram", x="Nous suivre sur X",
    rss="Ajouter le flux RSS", home="Aller à l’accueil", again="Fêter encore",
    unsub="Vous pouvez vous désabonner grâce au lien en bas de chaque e-mail."),
"ar": dict(title="أهلًا بك معنا", desc="تم تأكيد اشتراكك في النشرة الإخبارية من Nordic Crypto.", h1="أهلًا بك معنا!",
    lead="تم تأكيد اشتراكك. يصل عدد جديد إلى بريدك صباح كل يوم اثنين.", week_h="كل أسبوع ستحصل على",
    p1="أهم أخبار العملات المشفرة في دول الشمال هذا الأسبوع", p2="التنظيم وMiCA بشرح مبسّط",
    p3="الفعاليات القادمة في دول الشمال", p4="ملخص فيديو قصير للأسبوع",
    s_issues="عددًا حتى الآن", s_langs="لغة", s_stories="خبرًا في أحدث عدد", next_h="العدد القادم بعد",
    d="أيام", h="ساعات", m="دقيقة", s="ثانية", read="اقرأ أحدث عدد", tg="دردش معنا على Telegram", x="تابعنا على X",
    rss="أضف موجز RSS", home="إلى الصفحة الرئيسية", again="احتفل مرة أخرى",
    unsub="يمكنك إلغاء الاشتراك عبر الرابط في أسفل كل رسالة."),
"bn": dict(title="স্বাগতম", desc="Nordic Crypto নিউজলেটারে আপনার সাবস্ক্রিপশন নিশ্চিত হয়েছে।", h1="স্বাগতম!",
    lead="আপনার সাবস্ক্রিপশন নিশ্চিত হয়েছে। প্রতি সোমবার সকালে নতুন সংখ্যা আপনার ইনবক্সে পৌঁছাবে।", week_h="প্রতি সপ্তাহে আপনি পাবেন",
    p1="নর্ডিক দেশগুলোর সপ্তাহের সবচেয়ে গুরুত্বপূর্ণ ক্রিপ্টো খবর", p2="নিয়ন্ত্রণ ও MiCA, সহজ ভাষায়",
    p3="নর্ডিক দেশগুলোতে আসন্ন অনুষ্ঠান", p4="সপ্তাহের একটি ছোট ভিডিও সারসংক্ষেপ",
    s_issues="সংখ্যা এ পর্যন্ত", s_langs="ভাষা", s_stories="খবর সর্বশেষ সংখ্যায়", next_h="পরবর্তী সংখ্যা আসতে বাকি",
    d="দিন", h="ঘণ্টা", m="মিনিট", s="সেকেন্ড", read="সর্বশেষ সংখ্যা পড়ুন", tg="Telegram-এ চ্যাট করুন", x="X-এ অনুসরণ করুন",
    rss="RSS ফিড যোগ করুন", home="প্রথম পাতায় যান", again="আবার উদযাপন করুন",
    unsub="প্রতিটি ইমেলের নিচের লিংক দিয়ে আপনি সাবস্ক্রিপশন বাতিল করতে পারেন।"),
"pt": dict(title="Bem-vindo a bordo", desc="A sua subscrição da newsletter da Nordic Crypto está confirmada.", h1="Bem-vindo a bordo!",
    lead="A sua subscrição está confirmada. Todas as segundas-feiras de manhã chega um novo número à sua caixa de entrada.", week_h="Todas as semanas recebe",
    p1="As notícias cripto mais importantes dos países nórdicos", p2="Regulação e MiCA, explicadas de forma simples",
    p3="Próximos eventos nos países nórdicos", p4="Um breve resumo da semana em vídeo",
    s_issues="números até agora", s_langs="línguas", s_stories="notícias no último número", next_h="Próximo número dentro de",
    d="dias", h="horas", m="min", s="s", read="Ler o último número", tg="Converse no Telegram", x="Siga-nos no X",
    rss="Adicionar o feed RSS", home="Ir para a página inicial", again="Celebrar outra vez",
    unsub="Pode cancelar a subscrição com a ligação no fundo de cada e-mail."),
"ru": dict(title="Добро пожаловать", desc="Ваша подписка на рассылку Nordic Crypto подтверждена.", h1="Добро пожаловать!",
    lead="Подписка подтверждена. Новый выпуск будет приходить вам на почту каждый понедельник утром.", week_h="Каждую неделю вы получаете",
    p1="Главные криптоновости Северных стран за неделю", p2="Регулирование и MiCA простыми словами",
    p3="Ближайшие мероприятия в Северных странах", p4="Короткий видеообзор недели",
    s_issues="выпусков на сегодня", s_langs="языка", s_stories="новостей в последнем выпуске", next_h="Следующий выпуск через",
    d="дн.", h="ч", m="мин", s="сек", read="Читать последний выпуск", tg="Общаться в Telegram", x="Читать нас в X",
    rss="Добавить RSS-ленту", home="На главную", again="Отпраздновать ещё раз",
    unsub="Отписаться можно по ссылке внизу каждого письма."),
"ur": dict(title="خوش آمدید", desc="Nordic Crypto نیوز لیٹر کے لیے آپ کی رکنیت کی تصدیق ہو گئی ہے۔", h1="خوش آمدید!",
    lead="آپ کی رکنیت کی تصدیق ہو گئی ہے۔ ہر پیر کی صبح نیا شمارہ آپ کے ان باکس میں پہنچے گا۔", week_h="ہر ہفتے آپ کو ملے گا",
    p1="نارڈک ممالک سے ہفتے کی اہم ترین کرپٹو خبریں", p2="ضوابط اور MiCA، آسان الفاظ میں",
    p3="نارڈک ممالک میں آنے والی تقریبات", p4="ہفتے کا مختصر ویڈیو خلاصہ",
    s_issues="شمارے اب تک", s_langs="زبانیں", s_stories="خبریں تازہ شمارے میں", next_h="اگلا شمارہ آنے میں",
    d="دن", h="گھنٹے", m="منٹ", s="سیکنڈ", read="تازہ شمارہ پڑھیں", tg="Telegram پر بات کریں", x="X پر فالو کریں",
    rss="RSS فیڈ شامل کریں", home="سرورق پر جائیں", again="دوبارہ جشن منائیں",
    unsub="ہر ای میل کے نیچے دیے گئے لنک سے آپ رکنیت ختم کر سکتے ہیں۔"),
"id": dict(title="Selamat bergabung", desc="Langganan buletin Nordic Crypto Anda sudah dikonfirmasi.", h1="Selamat bergabung!",
    lead="Langganan Anda sudah dikonfirmasi. Edisi baru tiba di kotak masuk Anda setiap Senin pagi.", week_h="Setiap minggu Anda mendapat",
    p1="Berita kripto terpenting minggu ini dari negara-negara Nordik", p2="Regulasi dan MiCA, dijelaskan dengan sederhana",
    p3="Acara mendatang di negara-negara Nordik", p4="Rangkuman video singkat minggu ini",
    s_issues="edisi sejauh ini", s_langs="bahasa", s_stories="berita di edisi terbaru", next_h="Edisi berikutnya dalam",
    d="hari", h="jam", m="mnt", s="dtk", read="Baca edisi terbaru", tg="Ngobrol di Telegram", x="Ikuti di X",
    rss="Tambahkan feed RSS", home="Ke halaman depan", again="Rayakan lagi",
    unsub="Anda bisa berhenti berlangganan lewat tautan di bagian bawah setiap email."),
"de": dict(title="Willkommen an Bord", desc="Ihr Abonnement des Nordic-Crypto-Newsletters ist bestätigt.", h1="Willkommen an Bord!",
    lead="Ihr Abonnement ist bestätigt. Jeden Montagmorgen landet eine neue Ausgabe in Ihrem Posteingang.", week_h="Jede Woche erhalten Sie",
    p1="Die wichtigsten Krypto-Nachrichten der Woche aus dem Norden", p2="Regulierung und MiCA, verständlich erklärt",
    p3="Kommende Veranstaltungen in den nordischen Ländern", p4="Einen kurzen Video-Rückblick auf die Woche",
    s_issues="Ausgaben bisher", s_langs="Sprachen", s_stories="Meldungen in der neuesten Ausgabe", next_h="Nächste Ausgabe in",
    d="Tage", h="Std.", m="Min.", s="Sek.", read="Neueste Ausgabe lesen", tg="Auf Telegram chatten", x="Auf X folgen",
    rss="RSS-Feed hinzufügen", home="Zur Startseite", again="Nochmal feiern",
    unsub="Abmelden können Sie sich jederzeit über den Link am Ende jeder E-Mail."),
"ja": dict(title="ようこそ", desc="Nordic Crypto ニュースレターの購読が確認されました。", h1="ようこそ！",
    lead="購読が確認されました。毎週月曜日の朝、新しい号が受信トレイに届きます。", week_h="毎週お届けするもの",
    p1="北欧の今週の重要な暗号資産ニュース", p2="規制と MiCA をわかりやすく解説", p3="北欧で開催予定のイベント", p4="今週を振り返る短い動画",
    s_issues="号を発行", s_langs="言語", s_stories="本の記事（最新号）", next_h="次号まであと",
    d="日", h="時間", m="分", s="秒", read="最新号を読む", tg="Telegram で話す", x="X でフォロー",
    rss="RSS フィードを追加", home="トップページへ", again="もう一度お祝い", unsub="各メールの末尾のリンクからいつでも購読を解除できます。"),
"sw": dict(title="Karibu ndani", desc="Usajili wako wa jarida la Nordic Crypto umethibitishwa.", h1="Karibu ndani!",
    lead="Usajili wako umethibitishwa. Toleo jipya litafika kwenye kikasha chako kila Jumatatu asubuhi.", week_h="Kila wiki utapata",
    p1="Habari muhimu zaidi za kripto za wiki kutoka nchi za Nordiki", p2="Udhibiti na MiCA, vimeelezwa kwa lugha rahisi",
    p3="Matukio yajayo katika nchi za Nordiki", p4="Muhtasari mfupi wa video wa wiki",
    s_issues="matoleo hadi sasa", s_langs="lugha", s_stories="habari katika toleo jipya", next_h="Toleo lijalo baada ya",
    d="siku", h="saa", m="dak", s="sek", read="Soma toleo jipya", tg="Ongea nasi Telegram", x="Tufuate kwenye X",
    rss="Ongeza mlisho wa RSS", home="Nenda ukurasa wa mbele", again="Sherehekea tena",
    unsub="Unaweza kujiondoa kupitia kiungo kilicho chini ya kila barua pepe."),
"mr": dict(title="स्वागत आहे", desc="Nordic Crypto वृत्तपत्राच्या तुमच्या सदस्यत्वाची पुष्टी झाली आहे.", h1="स्वागत आहे!",
    lead="तुमच्या सदस्यत्वाची पुष्टी झाली आहे. दर सोमवारी सकाळी नवा अंक तुमच्या इनबॉक्समध्ये येईल.", week_h="दर आठवड्याला तुम्हाला मिळेल",
    p1="नॉर्डिक देशांतील आठवड्याच्या सर्वात महत्त्वाच्या क्रिप्टो बातम्या", p2="नियमन आणि MiCA, सोप्या शब्दांत",
    p3="नॉर्डिक देशांतील आगामी कार्यक्रम", p4="आठवड्याचा छोटा व्हिडिओ आढावा",
    s_issues="अंक आतापर्यंत", s_langs="भाषा", s_stories="बातम्या ताज्या अंकात", next_h="पुढचा अंक येण्यास",
    d="दिवस", h="तास", m="मिनिटे", s="सेकंद", read="ताजा अंक वाचा", tg="Telegram वर गप्पा मारा", x="X वर फॉलो करा",
    rss="RSS फीड जोडा", home="मुखपृष्ठावर जा", again="पुन्हा आनंद साजरा करा",
    unsub="प्रत्येक ईमेलच्या तळाशी असलेल्या दुव्याने तुम्ही सदस्यत्व रद्द करू शकता."),
"fa": dict(title="خوش آمدید", desc="اشتراک شما در خبرنامهٔ Nordic Crypto تأیید شد.", h1="خوش آمدید!",
    lead="اشتراک شما تأیید شد. هر دوشنبه صبح شمارهٔ تازه‌ای به صندوق ورودی شما می‌رسد.", week_h="هر هفته دریافت می‌کنید",
    p1="مهم‌ترین خبرهای رمزارز کشورهای نوردیک در این هفته", p2="مقررات و MiCA به زبان ساده",
    p3="رویدادهای پیش رو در کشورهای نوردیک", p4="خلاصهٔ ویدیویی کوتاه هفته",
    s_issues="شماره تا امروز", s_langs="زبان", s_stories="خبر در تازه‌ترین شماره", next_h="شمارهٔ بعدی تا",
    d="روز", h="ساعت", m="دقیقه", s="ثانیه", read="تازه‌ترین شماره را بخوانید", tg="در Telegram گفت‌وگو کنید", x="ما را در X دنبال کنید",
    rss="افزودن خوراک RSS", home="رفتن به صفحهٔ اصلی", again="دوباره جشن بگیرید",
    unsub="با پیوند پایین هر ایمیل می‌توانید اشتراک را لغو کنید."),
"uk": dict(title="Ласкаво просимо", desc="Вашу підписку на розсилку Nordic Crypto підтверджено.", h1="Ласкаво просимо!",
    lead="Підписку підтверджено. Новий випуск надходитиме на вашу пошту щопонеділка зранку.", week_h="Щотижня ви отримуєте",
    p1="Найважливіші криптоновини тижня з Північних країн", p2="Регулювання та MiCA простими словами",
    p3="Найближчі події в Північних країнах", p4="Короткий відеоогляд тижня",
    s_issues="випусків на сьогодні", s_langs="мови", s_stories="новин в останньому випуску", next_h="Наступний випуск через",
    d="дн.", h="год", m="хв", s="с", read="Читати останній випуск", tg="Спілкуватися в Telegram", x="Стежити в X",
    rss="Додати RSS-стрічку", home="На головну", again="Святкувати ще раз",
    unsub="Відписатися можна за посиланням унизу кожного листа."),
"tr": dict(title="Aramıza hoş geldiniz", desc="Nordic Crypto bültenine aboneliğiniz onaylandı.", h1="Aramıza hoş geldiniz!",
    lead="Aboneliğiniz onaylandı. Her pazartesi sabahı yeni sayı gelen kutunuzda olacak.", week_h="Her hafta şunları alırsınız",
    p1="İskandinav ülkelerinden haftanın en önemli kripto haberleri", p2="Düzenlemeler ve MiCA, sade bir dille",
    p3="İskandinav ülkelerinde yaklaşan etkinlikler", p4="Haftanın kısa bir video özeti",
    s_issues="sayı yayımlandı", s_langs="dil", s_stories="haber son sayıda", next_h="Sonraki sayıya kalan",
    d="gün", h="saat", m="dk", s="sn", read="Son sayıyı okuyun", tg="Telegram'da sohbet edin", x="X'te takip edin",
    rss="RSS akışını ekleyin", home="Ana sayfaya git", again="Bir daha kutla",
    unsub="Her e-postanın altındaki bağlantıyla aboneliğinizi iptal edebilirsiniz."),
"se": dict(title="Bures boahtin", desc="Du Nordic Crypto-ođasreivve diŋgojupmi lea duođaštuvvon.", h1="Bures boahtin!",
    lead="Du diŋgojupmi lea duođaštuvvon. Ođđa nummir boahtá du e-poastii juohke vuossárgga iđđes.", week_h="Juohke vahku don oaččut",
    p1="Vahkku deháleamos kryptoođđasat Davviriikkain", p2="Regulerema ja MiCA, čilgejuvvon álkidit",
    p3="Boahtte doaluid Davviriikkain", p4="Oanehis videočoahkkáigeassu vahkus",
    s_issues="nummira dássážii", s_langs="giela", s_stories="ášši ođđaseamos nummiris", next_h="Boahtte nummir",
    d="beaivvi", h="diimmu", m="min", s="sek", read="Loga ođđaseamos nummira", tg="Ságastala Telegramis", x="Čuovo min X:s",
    rss="Lasit RSS-rávdnji", home="Ovdasiidui", again="Ávvudala vel oktii",
    unsub="Sáhtát heaitit diŋgojumi liŋkkain juohke e-poastta vuolemus."),
}
for _l, _r in S.items():
    assert set(_r) == set(KEYS), (_l, set(KEYS) ^ set(_r))

ICONS = {
    "p1": '<path d="M4 5h13v14H6a2 2 0 0 1-2-2zM17 9h3v8a2 2 0 0 1-2 2M8 9h5M8 13h5"/>',
    "p2": '<path d="M12 3v18M5 7h14M7 7l-3 7a3 3 0 0 0 6 0zM17 7l-3 7a3 3 0 0 0 6 0zM8 21h8"/>',
    "p3": '<path d="M4 6h16v14H4zM4 10h16M8 3v5M16 3v5"/>',
    "p4": '<path d="M4 6h11v12H4zM15 10l5-3v10l-5-3"/>',
}

SHIELD = ('<svg class="shield" viewBox="6.4 2.4 51.2 60.2" aria-hidden="true" focusable="false">'
    '<defs><clipPath id="sc"><path d="M8 4H56V30C56 46 46 56 32 61C18 56 8 46 8 30Z"/></clipPath>'
    '<linearGradient id="gl" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
    '<stop offset=".5" stop-color="#fff" stop-opacity=".85"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>'
    '<g clip-path="url(#sc)"><path class="sh-l" fill="#1E3A45" d="M8 4H32V61C18 56 8 46 8 30Z"/><path class="sh-r" fill="#D9A034" d="M32 4H56V30C56 46 46 56 32 61Z"/>'
    '<g class="sh-key"><path fill="#D9A034" d="M32 8.5A8.5 8.5 0 0 0 32 25.5L32 20.8A3.8 3.8 0 0 1 32 13.2ZM28.6 24H32V49H28.6Z"/>'
    '<path fill="#1E3A45" d="M32 8.5A8.5 8.5 0 0 1 32 25.5L32 20.8A3.8 3.8 0 0 0 32 13.2ZM32 24H35.4V49H32ZM35.4 36.5H45V41H40.5V44.5H45V49H35.4Z"/></g>'
    '<rect class="sh-glint" x="-30" y="0" width="18" height="70" fill="url(#gl)"/></g>'
    '<path class="sh-o" pathLength="1" fill="none" stroke="#D9A034" stroke-width="2.4" stroke-linejoin="round" d="M8 4H56V30C56 46 46 56 32 61C18 56 8 46 8 30Z"/></svg>')


HEAD_JS = ('<script>(function(d){d.classList.add("js");if(!(window.matchMedia&&matchMedia("(prefers-reduced-motion: reduce)").matches)){d.classList.add("go");window.__ncF=setTimeout(function(){[].forEach.call(document.querySelectorAll(".card,.stats,.cta,.foot"),function(e){e.classList.add("in")})},6000)}})(document.documentElement)</script>')


def render(lang, html_lang, rtl, root, rel, latest_url, rss_url, issues, langs, stories, telegram, x_url):
    t = S.get(lang) or S["en"]
    perks = "".join(f'<li style="--i:{n}"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">{ICONS[k]}</svg><span>{E(t[k])}</span></li>'
                    for n, k in enumerate(("p1", "p2", "p3", "p4")))
    stats = "".join(f'<li><b data-count="{v}">{v}</b><span>{E(t[k])}</span></li>'
                    for v, k in ((issues, "s_issues"), (langs, "s_langs"), (stories, "s_stories")) if v)
    cd = "".join(f'<span class="cd-u"><b data-u="{u}">00</b><span>{E(t[u])}</span></span>' for u in ("d", "h", "m", "s"))
    cfg = json.dumps({"type": [t[k] for k in ("p1", "p2", "p3", "p4")]}, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="{html_lang}"{' dir="rtl"' if rtl else ''}><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex, nofollow"><meta name="referrer" content="no-referrer"><meta name="theme-color" content="#0B1B21">
<title>{E(t["title"])} – Nordic Crypto</title><meta name="description" content="{E(t["desc"])}">
<link rel="icon" href="{root}favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="{root}assets/brand/mark-180.png">
<link rel="stylesheet" href="{root}assets/subscribed/subscribed.css">
{HEAD_JS}</head>
<body>
<div class="sky-static" aria-hidden="true"></div><canvas id="sky" aria-hidden="true"></canvas><canvas id="fx" aria-hidden="true"></canvas>
<header class="bar"><a class="brand" href="{rel}"><img src="{root}assets/brand/shield-band.svg" width="26" height="31" alt=""><span>Nordic <i>Crypto</i></span></a></header>
<main id="main">
<section class="hero">
<div class="emblem"><span class="ring" aria-hidden="true"></span><span class="ring r2" aria-hidden="true"></span>{SHIELD}</div>
<h1 class="kin"><span class="vh">{E(t["h1"])}</span><span class="kin-a" aria-hidden="true">{E(t["h1"])}</span></h1>
<p class="lead">{E(t["lead"])}</p>
<p class="type" aria-hidden="true"><span id="tw"></span><span class="caret"></span></p>
</section>
<section class="card week" aria-labelledby="wk"><h2 id="wk">{E(t["week_h"])}</h2><ul class="perks">{perks}</ul></section>
{f'<section class="stats"><ul>{stats}</ul></section>' if stats else ''}
<section class="card next" aria-labelledby="nx"><h2 id="nx">{E(t["next_h"])}</h2><p class="cd" id="cd">{cd}</p></section>
<nav class="cta" aria-label="{E(t["title"])}">
<a class="btn gold" href="{E(latest_url)}">{E(t["read"])}</a>
<a class="btn" href="{E(telegram)}" rel="noopener">{E(t["tg"])}</a>
<a class="btn" href="{E(x_url)}" rel="noopener">{E(t["x"])}</a>
<a class="btn" href="{E(rss_url)}">{E(t["rss"])}</a>
<button class="btn ghost" type="button" id="again" hidden>{E(t["again"])}</button>
</nav>
<p class="foot"><a href="{rel}">{E(t["home"])}</a><br>{E(t["unsub"])}</p>
</main>
<script id="sub-cfg" type="application/json">{cfg}</script>
<script src="{root}assets/subscribed/subscribed.js" defer></script>
</body></html>
"""
