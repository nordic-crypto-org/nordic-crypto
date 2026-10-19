// Texts for the newsletter emails and the worker's own small unsubscribe page, per site and language.
// Kryptonytt rule: Norwegian text never says "AI"/"KI" (none of these texts mention it at all).
// Placeholders: {name} publication name, {link} confirmation/unsubscribe link, {site} site URL.
import siteUrl from "../../site_url.json" with { type: "json" };
const SITE_BASE = siteUrl.base.endsWith("/") ? siteUrl.base : siteUrl.base + "/";
export const SITES = {
  "nordic-crypto": { name: "Nordic Crypto", base: SITE_BASE, page: "newsletter/",
    langs: { en: "", nn: "nn/", nb: "nb/", sv: "sv/", da: "da/", fi: "fi/", is: "is/", zh: "zh/", hi: "hi/", es: "es/", fr: "fr/", ar: "ar/", bn: "bn/", pt: "pt/", ru: "ru/", ur: "ur/", id: "id/", de: "de/", ja: "ja/", sw: "sw/", mr: "mr/", fa: "fa/", uk: "uk/", tr: "tr/", se: "se/" }, def: "en", done: "subscribed/" },
  "kryptonytt": { name: "Kryptonytt Norge", base: "https://jqrgen.github.io/kryptonytt/", page: "nyhetsbrev/",
    langs: { nn: "", nb: "bm/", en: "en/" }, def: "nn" },
};
export const pageUrl = (site, lang) => { const s = SITES[site]; return s.base + (s.langs[lang] ?? "") + s.page; };
export const doneUrl = (site, lang) => { const s = SITES[site]; return s.done ? s.base + (s.langs[lang] ?? "") + s.done : pageUrl(site, lang) + "?confirmed=1"; };
export const dir = (lang) => (["ar", "fa", "ur"].includes(lang) ? ' dir="rtl"' : "");

const T = {
  en: { cs: "Confirm your {name} newsletter subscription",
        cb: "Hi,\n\nSomeone (hopefully you) asked to receive the {name} newsletter at this address. Please confirm by opening this link within 7 days:\n\n{link}\n\nIf it wasn't you, just ignore this email: nothing more will be sent, and the address is deleted after 7 days.\n\n{name} – {site}\n",
        ws: "Welcome to the {name} newsletter",
        wb: "Thanks, your subscription is confirmed. You'll get a short weekly digest of the stories our editor has approved, with links to the original sources.\n\nYou can unsubscribe at any time with this link (it is also in every newsletter):\n{link}\n\n{name} – {site}\n",
        ut: "Unsubscribe", uq: "Unsubscribe from the {name} newsletter?", ub: "Yes, unsubscribe", ux: "This link is invalid." },
  nn: { cs: "Stadfest abonnementet på nyheitsbrevet frå {name}",
        cb: "Hei,\n\nNokon (forhåpentleg du) har bede om å få nyheitsbrevet frå {name} til denne adressa. Stadfest ved å opne denne lenkja innan 7 dagar:\n\n{link}\n\nVar det ikkje deg, kan du berre sjå bort frå denne e-posten: du får ikkje fleire, og adressa blir sletta etter 7 dagar.\n\n{name} – {site}\n",
        ws: "Velkomen til nyheitsbrevet frå {name}",
        wb: "Takk, abonnementet ditt er stadfesta. Du får eit kort samandrag kvar veke av sakene redaktøren vår har godkjent, med lenkjer til kjeldene.\n\nDu kan melde deg av når du vil med denne lenkja (ho står også i kvart nyheitsbrev):\n{link}\n\n{name} – {site}\n",
        ut: "Meld av", uq: "Vil du melde deg av nyheitsbrevet frå {name}?", ub: "Ja, meld meg av", ux: "Lenkja er ugyldig." },
  nb: { cs: "Bekreft abonnementet på nyhetsbrevet fra {name}",
        cb: "Hei,\n\nNoen (forhåpentligvis du) har bedt om å få nyhetsbrevet fra {name} til denne adressen. Bekreft ved å åpne denne lenken innen 7 dager:\n\n{link}\n\nVar det ikke deg, kan du bare se bort fra denne e-posten: du får ikke flere, og adressen slettes etter 7 dager.\n\n{name} – {site}\n",
        ws: "Velkommen til nyhetsbrevet fra {name}",
        wb: "Takk, abonnementet ditt er bekreftet. Du får et kort sammendrag hver uke av sakene redaktøren vår har godkjent, med lenker til kildene.\n\nDu kan melde deg av når du vil med denne lenken (den står også i hvert nyhetsbrev):\n{link}\n\n{name} – {site}\n",
        ut: "Meld av", uq: "Vil du melde deg av nyhetsbrevet fra {name}?", ub: "Ja, meld meg av", ux: "Lenken er ugyldig." },
  sv: { cs: "Bekräfta din prenumeration på nyhetsbrevet från {name}",
        cb: "Hej,\n\nNågon (förhoppningsvis du) har bett om att få nyhetsbrevet från {name} till den här adressen. Bekräfta genom att öppna länken inom 7 dagar:\n\n{link}\n\nVar det inte du kan du bortse från det här mejlet: inget mer skickas, och adressen raderas efter 7 dagar.\n\n{name} – {site}\n",
        ws: "Välkommen till nyhetsbrevet från {name}",
        wb: "Tack, din prenumeration är bekräftad. Du får en kort sammanfattning varje vecka av de nyheter som vår redaktör har godkänt, med länkar till källorna.\n\nDu kan avsluta prenumerationen när du vill med den här länken (den finns också i varje nyhetsbrev):\n{link}\n\n{name} – {site}\n",
        ut: "Avsluta prenumeration", uq: "Vill du avsluta prenumerationen på nyhetsbrevet från {name}?", ub: "Ja, avsluta", ux: "Länken är ogiltig." },
  da: { cs: "Bekræft dit abonnement på nyhedsbrevet fra {name}",
        cb: "Hej,\n\nNogen (forhåbentlig dig) har bedt om at få nyhedsbrevet fra {name} på denne adresse. Bekræft ved at åbne linket inden for 7 dage:\n\n{link}\n\nVar det ikke dig, kan du bare se bort fra denne e-mail: der sendes ikke mere, og adressen slettes efter 7 dage.\n\n{name} – {site}\n",
        ws: "Velkommen til nyhedsbrevet fra {name}",
        wb: "Tak, dit abonnement er bekræftet. Du får et kort ugentligt overblik over de historier, vores redaktør har godkendt, med links til kilderne.\n\nDu kan til enhver tid afmelde dig med dette link (det står også i hvert nyhedsbrev):\n{link}\n\n{name} – {site}\n",
        ut: "Afmeld", uq: "Vil du afmelde nyhedsbrevet fra {name}?", ub: "Ja, afmeld mig", ux: "Linket er ugyldigt." },
  fi: { cs: "Vahvista {name}-uutiskirjeen tilaus",
        cb: "Hei,\n\nJoku (toivottavasti sinä) on pyytänyt {name}-uutiskirjettä tähän osoitteeseen. Vahvista tilaus avaamalla tämä linkki 7 päivän kuluessa:\n\n{link}\n\nJos et tilannut uutiskirjettä, voit jättää tämän viestin huomiotta: muuta ei lähetetä, ja osoite poistetaan 7 päivän kuluttua.\n\n{name} – {site}\n",
        ws: "Tervetuloa {name}-uutiskirjeen tilaajaksi",
        wb: "Kiitos, tilauksesi on vahvistettu. Saat joka viikko lyhyen koosteen toimittajamme hyväksymistä uutisista ja linkit alkuperäisiin lähteisiin.\n\nVoit perua tilauksen milloin tahansa tällä linkillä (se on myös jokaisessa uutiskirjeessä):\n{link}\n\n{name} – {site}\n",
        ut: "Peru tilaus", uq: "Haluatko perua {name}-uutiskirjeen tilauksen?", ub: "Kyllä, peru tilaus", ux: "Linkki ei ole voimassa." },
  is: { cs: "Staðfestu áskrift að fréttabréfi {name}",
        cb: "Hæ,\n\nEinhver (vonandi þú) hefur beðið um að fá fréttabréf {name} á þetta netfang. Staðfestu með því að opna þennan tengil innan 7 daga:\n\n{link}\n\nEf þetta varst ekki þú geturðu hunsað þennan póst: ekkert fleira verður sent og netfanginu verður eytt eftir 7 daga.\n\n{name} – {site}\n",
        ws: "Velkomin(n) á fréttabréf {name}",
        wb: "Takk, áskriftin þín er staðfest. Þú færð stutta vikulega samantekt um fréttir sem ritstjórinn okkar hefur samþykkt, með tenglum á heimildirnar.\n\nÞú getur sagt upp áskriftinni hvenær sem er með þessum tengli (hann er líka í hverju fréttabréfi):\n{link}\n\n{name} – {site}\n",
        ut: "Segja upp áskrift", uq: "Viltu segja upp áskrift að fréttabréfi {name}?", ub: "Já, segja upp", ux: "Tengillinn er ógildur." },
  zh: { cs: "请确认订阅 {name} 新闻通讯",
        cb: "您好，\n\n有人（希望是您）请求将 {name} 新闻通讯发送到此地址。请在 7 天内打开以下链接确认：\n\n{link}\n\n如果不是您本人，请忽略此邮件：我们不会再发送任何邮件，该地址将在 7 天后删除。\n\n{name} – {site}\n",
        ws: "欢迎订阅 {name} 新闻通讯",
        wb: "谢谢，您的订阅已确认。每周您将收到一份简短摘要，汇总经我们编辑审核的新闻，并附原始来源链接。\n\n您可以随时通过此链接退订（每期新闻通讯中也有）：\n{link}\n\n{name} – {site}\n",
        ut: "退订", uq: "要退订 {name} 新闻通讯吗？", ub: "是的，退订", ux: "此链接无效。" },
  hi: { cs: "{name} न्यूज़लेटर की सदस्यता की पुष्टि करें",
        cb: "नमस्ते,\n\nकिसी ने (उम्मीद है आपने) इस पते पर {name} न्यूज़लेटर पाने का अनुरोध किया है। कृपया 7 दिनों के भीतर यह लिंक खोलकर पुष्टि करें:\n\n{link}\n\nअगर यह आप नहीं थे, तो इस ईमेल को अनदेखा करें: आगे कुछ नहीं भेजा जाएगा, और 7 दिनों के बाद पता हटा दिया जाएगा।\n\n{name} – {site}\n",
        ws: "{name} न्यूज़लेटर में आपका स्वागत है",
        wb: "धन्यवाद, आपकी सदस्यता की पुष्टि हो गई है। हर हफ़्ते आपको हमारे संपादक द्वारा स्वीकृत ख़बरों का एक छोटा सारांश मिलेगा, मूल स्रोतों के लिंक के साथ।\n\nआप इस लिंक से कभी भी सदस्यता छोड़ सकते हैं (यह हर न्यूज़लेटर में भी है):\n{link}\n\n{name} – {site}\n",
        ut: "सदस्यता छोड़ें", uq: "{name} न्यूज़लेटर की सदस्यता छोड़ें?", ub: "हाँ, सदस्यता छोड़ें", ux: "यह लिंक अमान्य है।" },
  es: { cs: "Confirma tu suscripción al boletín de {name}",
        cb: "Hola:\n\nAlguien (esperamos que tú) ha pedido recibir el boletín de {name} en esta dirección. Confírmalo abriendo este enlace en un plazo de 7 días:\n\n{link}\n\nSi no has sido tú, ignora este correo: no se enviará nada más y la dirección se borrará al cabo de 7 días.\n\n{name} – {site}\n",
        ws: "Te damos la bienvenida al boletín de {name}",
        wb: "Gracias, tu suscripción está confirmada. Cada semana recibirás un breve resumen de las noticias aprobadas por nuestro editor, con enlaces a las fuentes originales.\n\nPuedes darte de baja en cualquier momento con este enlace (también aparece en cada boletín):\n{link}\n\n{name} – {site}\n",
        ut: "Darse de baja", uq: "¿Quieres darte de baja del boletín de {name}?", ub: "Sí, darme de baja", ux: "Este enlace no es válido." },
  fr: { cs: "Confirmez votre abonnement à la lettre d’information de {name}",
        cb: "Bonjour,\n\nQuelqu’un (vous, nous l’espérons) a demandé à recevoir la lettre d’information de {name} à cette adresse. Merci de confirmer en ouvrant ce lien dans les 7 jours :\n\n{link}\n\nSi ce n’était pas vous, ignorez simplement ce message : rien d’autre ne sera envoyé et l’adresse sera supprimée au bout de 7 jours.\n\n{name} – {site}\n",
        ws: "Bienvenue dans la lettre d’information de {name}",
        wb: "Merci, votre abonnement est confirmé. Vous recevrez chaque semaine un court résumé des articles approuvés par notre rédaction, avec des liens vers les sources originales.\n\nVous pouvez vous désabonner à tout moment avec ce lien (il figure aussi dans chaque lettre) :\n{link}\n\n{name} – {site}\n",
        ut: "Se désabonner", uq: "Se désabonner de la lettre d’information de {name} ?", ub: "Oui, me désabonner", ux: "Ce lien n’est pas valide." },
  ar: { cs: "أكّد اشتراكك في النشرة البريدية من {name}",
        cb: "مرحبًا،\n\nطلب شخص ما (نأمل أن تكون أنت) تلقي النشرة البريدية من {name} على هذا العنوان. يُرجى التأكيد بفتح هذا الرابط خلال 7 أيام:\n\n{link}\n\nإن لم تكن أنت، فتجاهل هذه الرسالة: لن يُرسل أي شيء آخر، وسيُحذف العنوان بعد 7 أيام.\n\n{name} – {site}\n",
        ws: "مرحبًا بك في النشرة البريدية من {name}",
        wb: "شكرًا، تم تأكيد اشتراكك. ستصلك كل أسبوع خلاصة قصيرة للأخبار التي وافق عليها محررنا، مع روابط إلى المصادر الأصلية.\n\nيمكنك إلغاء الاشتراك في أي وقت عبر هذا الرابط (وهو موجود أيضًا في كل نشرة):\n{link}\n\n{name} – {site}\n",
        ut: "إلغاء الاشتراك", uq: "هل تريد إلغاء الاشتراك في النشرة البريدية من {name}؟", ub: "نعم، ألغِ اشتراكي", ux: "هذا الرابط غير صالح." },
  bn: { cs: "{name} নিউজলেটারের সাবস্ক্রিপশন নিশ্চিত করুন",
        cb: "নমস্কার,\n\nকেউ (আশা করি আপনি) এই ঠিকানায় {name} নিউজলেটার পাওয়ার অনুরোধ করেছেন। অনুগ্রহ করে ৭ দিনের মধ্যে এই লিংকটি খুলে নিশ্চিত করুন:\n\n{link}\n\nযদি এটি আপনি না হন, এই ইমেলটি উপেক্ষা করুন: আর কিছু পাঠানো হবে না, এবং ৭ দিন পরে ঠিকানাটি মুছে ফেলা হবে।\n\n{name} – {site}\n",
        ws: "{name} নিউজলেটারে স্বাগতম",
        wb: "ধন্যবাদ, আপনার সাবস্ক্রিপশন নিশ্চিত হয়েছে। প্রতি সপ্তাহে আপনি আমাদের সম্পাদকের অনুমোদিত খবরের একটি ছোট সারসংক্ষেপ পাবেন, মূল সূত্রের লিংকসহ।\n\nএই লিংক দিয়ে আপনি যেকোনো সময় সাবস্ক্রিপশন বাতিল করতে পারেন (এটি প্রতিটি নিউজলেটারেও থাকে):\n{link}\n\n{name} – {site}\n",
        ut: "সাবস্ক্রিপশন বাতিল", uq: "{name} নিউজলেটারের সাবস্ক্রিপশন বাতিল করবেন?", ub: "হ্যাঁ, বাতিল করুন", ux: "এই লিংকটি অবৈধ।" },
  pt: { cs: "Confirme a sua subscrição da newsletter da {name}",
        cb: "Olá,\n\nAlguém (esperamos que tenha sido você) pediu para receber a newsletter da {name} neste endereço. Confirme abrindo esta ligação nos próximos 7 dias:\n\n{link}\n\nSe não foi você, ignore este e-mail: não será enviado mais nada e o endereço será apagado ao fim de 7 dias.\n\n{name} – {site}\n",
        ws: "Bem-vindo à newsletter da {name}",
        wb: "Obrigado, a sua subscrição está confirmada. Todas as semanas receberá um breve resumo das notícias aprovadas pelo nosso editor, com ligações para as fontes originais.\n\nPode cancelar a subscrição a qualquer momento com esta ligação (também está em cada newsletter):\n{link}\n\n{name} – {site}\n",
        ut: "Cancelar subscrição", uq: "Cancelar a subscrição da newsletter da {name}?", ub: "Sim, cancelar", ux: "Esta ligação não é válida." },
  ru: { cs: "Подтвердите подписку на рассылку {name}",
        cb: "Здравствуйте!\n\nКто-то (надеемся, вы) попросил присылать рассылку {name} на этот адрес. Подтвердите подписку, открыв эту ссылку в течение 7 дней:\n\n{link}\n\nЕсли это были не вы, просто проигнорируйте это письмо: больше ничего не придёт, а адрес будет удалён через 7 дней.\n\n{name} – {site}\n",
        ws: "Добро пожаловать в рассылку {name}",
        wb: "Спасибо, ваша подписка подтверждена. Каждую неделю вы будете получать короткую подборку новостей, одобренных нашим редактором, со ссылками на первоисточники.\n\nОтписаться можно в любой момент по этой ссылке (она есть и в каждом выпуске):\n{link}\n\n{name} – {site}\n",
        ut: "Отписаться", uq: "Отписаться от рассылки {name}?", ub: "Да, отписаться", ux: "Эта ссылка недействительна." },
  ur: { cs: "{name} نیوز لیٹر کی رکنیت کی تصدیق کریں",
        cb: "السلام علیکم،\n\nکسی نے (امید ہے آپ نے) اس پتے پر {name} نیوز لیٹر حاصل کرنے کی درخواست کی ہے۔ براہ کرم 7 دن کے اندر یہ لنک کھول کر تصدیق کریں:\n\n{link}\n\nاگر یہ آپ نہیں تھے تو اس ای میل کو نظر انداز کر دیں: مزید کچھ نہیں بھیجا جائے گا، اور 7 دن بعد پتہ حذف کر دیا جائے گا۔\n\n{name} – {site}\n",
        ws: "{name} نیوز لیٹر میں خوش آمدید",
        wb: "شکریہ، آپ کی رکنیت کی تصدیق ہو گئی ہے۔ ہر ہفتے آپ کو ہمارے ایڈیٹر کی منظور کردہ خبروں کا مختصر خلاصہ ملے گا، اصل ذرائع کے لنکس کے ساتھ۔\n\nآپ کسی بھی وقت اس لنک سے رکنیت ختم کر سکتے ہیں (یہ ہر نیوز لیٹر میں بھی ہوتا ہے):\n{link}\n\n{name} – {site}\n",
        ut: "رکنیت ختم کریں", uq: "کیا {name} نیوز لیٹر کی رکنیت ختم کرنی ہے؟", ub: "جی ہاں، رکنیت ختم کریں", ux: "یہ لنک درست نہیں ہے۔" },
  id: { cs: "Konfirmasi langganan buletin {name} Anda",
        cb: "Halo,\n\nSeseorang (semoga Anda) meminta buletin {name} dikirim ke alamat ini. Silakan konfirmasi dengan membuka tautan ini dalam 7 hari:\n\n{link}\n\nJika itu bukan Anda, abaikan saja email ini: tidak ada lagi yang akan dikirim, dan alamat ini dihapus setelah 7 hari.\n\n{name} – {site}\n",
        ws: "Selamat datang di buletin {name}",
        wb: "Terima kasih, langganan Anda sudah dikonfirmasi. Setiap minggu Anda akan menerima ringkasan singkat berita yang disetujui editor kami, dengan tautan ke sumber aslinya.\n\nAnda bisa berhenti berlangganan kapan saja lewat tautan ini (tautan ini juga ada di setiap buletin):\n{link}\n\n{name} – {site}\n",
        ut: "Berhenti berlangganan", uq: "Berhenti berlangganan buletin {name}?", ub: "Ya, berhenti berlangganan", ux: "Tautan ini tidak valid." },
  de: { cs: "Bestätigen Sie Ihr Abonnement des {name}-Newsletters",
        cb: "Hallo,\n\nJemand (hoffentlich Sie) hat den {name}-Newsletter für diese Adresse angefordert. Bitte bestätigen Sie, indem Sie diesen Link innerhalb von 7 Tagen öffnen:\n\n{link}\n\nWenn Sie das nicht waren, ignorieren Sie diese E-Mail einfach: Es wird nichts weiter verschickt, und die Adresse wird nach 7 Tagen gelöscht.\n\n{name} – {site}\n",
        ws: "Willkommen beim {name}-Newsletter",
        wb: "Danke, Ihr Abonnement ist bestätigt. Sie erhalten jede Woche eine kurze Zusammenfassung der von unserer Redaktion freigegebenen Meldungen, mit Links zu den Originalquellen.\n\nSie können sich jederzeit mit diesem Link abmelden (er steht auch in jedem Newsletter):\n{link}\n\n{name} – {site}\n",
        ut: "Abmelden", uq: "Vom {name}-Newsletter abmelden?", ub: "Ja, abmelden", ux: "Dieser Link ist ungültig." },
  ja: { cs: "{name} ニュースレターの購読を確認してください",
        cb: "こんにちは。\n\nどなたか（ご本人であることを願います）が、このアドレスで {name} ニュースレターの受信を希望されました。7日以内に次のリンクを開いて確認してください：\n\n{link}\n\nお心当たりがない場合は、このメールを無視してください。これ以上メールが届くことはなく、アドレスは7日後に削除されます。\n\n{name} – {site}\n",
        ws: "{name} ニュースレターへようこそ",
        wb: "ありがとうございます。購読が確認されました。毎週、編集者が承認したニュースの短いまとめを、元の情報源へのリンク付きでお届けします。\n\n購読はこのリンクからいつでも解除できます（各ニュースレターにも記載されています）：\n{link}\n\n{name} – {site}\n",
        ut: "購読解除", uq: "{name} ニュースレターの購読を解除しますか？", ub: "はい、解除します", ux: "このリンクは無効です。" },
  sw: { cs: "Thibitisha usajili wako wa jarida la {name}",
        cb: "Habari,\n\nMtu fulani (tunatumaini ni wewe) ameomba kupokea jarida la {name} kwenye anwani hii. Tafadhali thibitisha kwa kufungua kiungo hiki ndani ya siku 7:\n\n{link}\n\nKama si wewe, puuza barua pepe hii tu: hakuna kitakachotumwa tena, na anwani itafutwa baada ya siku 7.\n\n{name} – {site}\n",
        ws: "Karibu kwenye jarida la {name}",
        wb: "Asante, usajili wako umethibitishwa. Kila wiki utapokea muhtasari mfupi wa habari zilizoidhinishwa na mhariri wetu, pamoja na viungo vya vyanzo asili.\n\nUnaweza kujiondoa wakati wowote kwa kiungo hiki (kipo pia katika kila jarida):\n{link}\n\n{name} – {site}\n",
        ut: "Jiondoe", uq: "Ujiondoe kwenye jarida la {name}?", ub: "Ndiyo, niondoe", ux: "Kiungo hiki si sahihi." },
  mr: { cs: "{name} वृत्तपत्राच्या सदस्यत्वाची पुष्टी करा",
        cb: "नमस्कार,\n\nकोणीतरी (आशा आहे तुम्हीच) या पत्त्यावर {name} वृत्तपत्र मिळावे अशी विनंती केली आहे. कृपया 7 दिवसांच्या आत हा दुवा उघडून पुष्टी करा:\n\n{link}\n\nहे तुम्ही नसाल, तर या ईमेलकडे दुर्लक्ष करा: पुढे काहीही पाठवले जाणार नाही, आणि 7 दिवसांनंतर पत्ता हटवला जाईल.\n\n{name} – {site}\n",
        ws: "{name} वृत्तपत्रात तुमचे स्वागत आहे",
        wb: "धन्यवाद, तुमच्या सदस्यत्वाची पुष्टी झाली आहे. दर आठवड्याला तुम्हाला आमच्या संपादकाने मंजूर केलेल्या बातम्यांचा छोटा सारांश मूळ स्रोतांच्या दुव्यांसह मिळेल.\n\nया दुव्याने तुम्ही कधीही सदस्यत्व रद्द करू शकता (तो प्रत्येक वृत्तपत्रातही असतो):\n{link}\n\n{name} – {site}\n",
        ut: "सदस्यत्व रद्द करा", uq: "{name} वृत्तपत्राचे सदस्यत्व रद्द करायचे?", ub: "होय, सदस्यत्व रद्द करा", ux: "हा दुवा अवैध आहे." },
  fa: { cs: "اشتراک خود در خبرنامهٔ {name} را تأیید کنید",
        cb: "سلام،\n\nکسی (امیدواریم شما) درخواست کرده است خبرنامهٔ {name} به این نشانی فرستاده شود. لطفاً با باز کردن این پیوند ظرف 7 روز تأیید کنید:\n\n{link}\n\nاگر شما نبودید، این ایمیل را نادیده بگیرید: چیز دیگری فرستاده نمی‌شود و نشانی پس از 7 روز حذف می‌شود.\n\n{name} – {site}\n",
        ws: "به خبرنامهٔ {name} خوش آمدید",
        wb: "سپاس، اشتراک شما تأیید شد. هر هفته خلاصه‌ای کوتاه از خبرهایی که ویراستار ما تأیید کرده است، همراه با پیوند به منابع اصلی، دریافت می‌کنید.\n\nهر زمان بخواهید می‌توانید با این پیوند اشتراک را لغو کنید (این پیوند در هر خبرنامه هم هست):\n{link}\n\n{name} – {site}\n",
        ut: "لغو اشتراک", uq: "اشتراک خبرنامهٔ {name} لغو شود؟", ub: "بله، لغو کن", ux: "این پیوند نامعتبر است." },
  uk: { cs: "Підтвердьте підписку на розсилку {name}",
        cb: "Вітаємо!\n\nХтось (сподіваємося, ви) попросив надсилати розсилку {name} на цю адресу. Підтвердьте підписку, відкривши це посилання протягом 7 днів:\n\n{link}\n\nЯкщо це були не ви, просто проігноруйте цей лист: більше нічого не надійде, а адресу буде видалено через 7 днів.\n\n{name} – {site}\n",
        ws: "Ласкаво просимо до розсилки {name}",
        wb: "Дякуємо, вашу підписку підтверджено. Щотижня ви отримуватимете короткий огляд новин, схвалених нашим редактором, із посиланнями на першоджерела.\n\nВідписатися можна будь-коли за цим посиланням (воно є і в кожному випуску):\n{link}\n\n{name} – {site}\n",
        ut: "Відписатися", uq: "Відписатися від розсилки {name}?", ub: "Так, відписатися", ux: "Це посилання недійсне." },
  tr: { cs: "{name} bülteni aboneliğinizi onaylayın",
        cb: "Merhaba,\n\nBirisi (umarız sizsiniz) {name} bülteninin bu adrese gönderilmesini istedi. Lütfen 7 gün içinde bu bağlantıyı açarak onaylayın:\n\n{link}\n\nBu siz değilseniz bu e-postayı yok sayın: başka bir şey gönderilmeyecek ve adres 7 gün sonra silinecek.\n\n{name} – {site}\n",
        ws: "{name} bültenine hoş geldiniz",
        wb: "Teşekkürler, aboneliğiniz onaylandı. Her hafta editörümüzün onayladığı haberlerin kısa bir özetini, özgün kaynakların bağlantılarıyla birlikte alacaksınız.\n\nBu bağlantıyla istediğiniz zaman aboneliğinizi iptal edebilirsiniz (her bültende de yer alır):\n{link}\n\n{name} – {site}\n",
        ut: "Aboneliği iptal et", uq: "{name} bülteni aboneliği iptal edilsin mi?", ub: "Evet, iptal et", ux: "Bu bağlantı geçersiz." },
  se: { cs: "Duođaštus {name}-ođasreivve diŋgojumi",
        cb: "Bures,\n\nMuhtun (sávvamis don) lea bivdán oažžut {name}-ođasreivve dán čujuhussii. Duođaštuvvo rabastemiin dán liŋkka 7 beaivvi siste:\n\n{link}\n\nJus it lean don, de sáhtát dušše badjelgeahččat dán e-poastta: eanet ii sáddejuvvo, ja čujuhus sihkkojuvvo 7 beaivvi geažes.\n\n{name} – {site}\n",
        ws: "Bures boahtin {name}-ođasreivve lohkkin",
        wb: "Giitu, du diŋgojupmi lea duođaštuvvon. Juohke vahku oaččut oanehis čoahkkáigeasu ođđasiin maid min doaimmaheaddji lea dohkkehan, liŋkkaiguin álgogáldduide.\n\nSáhtát goas fal heaitit diŋgojumi dáinna liŋkkain (dat lea maiddái juohke ođasreivves):\n{link}\n\n{name} – {site}\n",
        ut: "Heaitte diŋgojumi", uq: "Háliidatgo heaitit {name}-ođasreivve diŋgojumi?", ub: "Juo, heaitte", ux: "Liŋka ii leat gustovaš." },
};
export const LANG_KEYS = Object.keys(T);
const fill = (s, v) => s.replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m));
export function text(lang, key, vars) { return fill((T[lang] || T.en)[key], vars || {}); }
export function confirmEmail(site, lang, link) {
  const v = { name: SITES[site].name, site: SITES[site].base + (SITES[site].langs[lang] ?? ""), link };
  const subject = text(lang, "cs", v), body = text(lang, "cb", v);
  return { subject, text: body, ...(site === "nordic-crypto" ? { html: emailHtml(site, lang, { title: subject, body, link, cta: true }) } : {}) };
}
export function welcomeEmail(site, lang, link) {
  const v = { name: SITES[site].name, site: SITES[site].base + (SITES[site].langs[lang] ?? ""), link };
  let body = text(lang, "wb", v);
  if (site === "nordic-crypto" && !body.includes("The Nordic Crypto team")) body += "The Nordic Crypto team\n";
  const subject = text(lang, "ws", v);
  return { subject, text: body, ...(site === "nordic-crypto" ? { html: emailHtml(site, lang, { title: subject, body, link, cta: false }) } : {}) };
}

// ---- Branded HTML alternative (Langskip palette, see nordiccrypto.no/media). Table layout + inline CSS for email clients.
// The text/plain body above stays the canonical version; html is sent alongside it.
const C = { sail: "#F0F1EC", pine: "#1D1C1A", sea: "#1E3A45", gold: "#D9A034", foam: "#BFD3D3" };
const F = { sans: "'Schibsted Grotesk',Helvetica,Arial,sans-serif", serif: "'Cormorant Garamond',Georgia,'Times New Roman',serif",
  mono: "'IBM Plex Mono',Menlo,Consolas,monospace" };
const LOGO = SITE_BASE + "assets/brand/mark-192.png";   // PNG on the live site (no SVG in email)
const B = {
  en: { btn: "Confirm subscription", alt: "Or copy this link into your browser:", visit: "Visit the site" },
  nn: { btn: "Stadfest abonnementet", alt: "Eller kopier denne lenkja inn i nettlesaren:", visit: "Gå til nettstaden" },
  nb: { btn: "Bekreft abonnementet", alt: "Eller kopier denne lenken inn i nettleseren:", visit: "Gå til nettstedet" },
  sv: { btn: "Bekräfta prenumerationen", alt: "Eller kopiera länken till din webbläsare:", visit: "Besök webbplatsen" },
  da: { btn: "Bekræft abonnementet", alt: "Eller kopiér linket ind i din browser:", visit: "Besøg sitet" },
  fi: { btn: "Vahvista tilaus", alt: "Tai kopioi tämä linkki selaimeesi:", visit: "Siirry sivustolle" },
  is: { btn: "Staðfesta áskrift", alt: "Eða afritaðu tengilinn í vafrann:", visit: "Fara á vefinn" },
  zh: { btn: "确认订阅", alt: "或将此链接复制到浏览器：", visit: "访问网站" },
  hi: { btn: "सदस्यता की पुष्टि करें", alt: "या यह लिंक अपने ब्राउज़र में कॉपी करें:", visit: "वेबसाइट पर जाएँ" },
  es: { btn: "Confirmar suscripción", alt: "O copia este enlace en tu navegador:", visit: "Visitar el sitio" },
  fr: { btn: "Confirmer l’abonnement", alt: "Ou copiez ce lien dans votre navigateur :", visit: "Visiter le site" },
  ar: { btn: "تأكيد الاشتراك", alt: "أو انسخ هذا الرابط في متصفحك:", visit: "زيارة الموقع" },
  bn: { btn: "সাবস্ক্রিপশন নিশ্চিত করুন", alt: "অথবা এই লিংকটি আপনার ব্রাউজারে কপি করুন:", visit: "ওয়েবসাইটে যান" },
  pt: { btn: "Confirmar subscrição", alt: "Ou copie esta ligação para o seu navegador:", visit: "Visitar o site" },
  ru: { btn: "Подтвердить подписку", alt: "Или скопируйте ссылку в браузер:", visit: "Перейти на сайт" },
  ur: { btn: "رکنیت کی تصدیق کریں", alt: "یا یہ لنک اپنے براؤزر میں کاپی کریں:", visit: "ویب سائٹ دیکھیں" },
  id: { btn: "Konfirmasi langganan", alt: "Atau salin tautan ini ke peramban Anda:", visit: "Kunjungi situs" },
  de: { btn: "Abonnement bestätigen", alt: "Oder kopieren Sie diesen Link in Ihren Browser:", visit: "Zur Website" },
  ja: { btn: "購読を確認する", alt: "またはこのリンクをブラウザにコピーしてください：", visit: "サイトを見る" },
  sw: { btn: "Thibitisha usajili", alt: "Au nakili kiungo hiki kwenye kivinjari chako:", visit: "Tembelea tovuti" },
  mr: { btn: "सदस्यत्वाची पुष्टी करा", alt: "किंवा हा दुवा तुमच्या ब्राउझरमध्ये कॉपी करा:", visit: "संकेतस्थळाला भेट द्या" },
  fa: { btn: "تأیید اشتراک", alt: "یا این پیوند را در مرورگر خود کپی کنید:", visit: "رفتن به وب‌سایت" },
  uk: { btn: "Підтвердити підписку", alt: "Або скопіюйте посилання у браузер:", visit: "Перейти на сайт" },
  tr: { btn: "Aboneliği onayla", alt: "Ya da bu bağlantıyı tarayıcınıza kopyalayın:", visit: "Siteyi ziyaret et" },
  se: { btn: "Duođaš diŋgojumi", alt: "Dahje máŋge dán liŋkka iežat neahttalohkkái:", visit: "Mana neahttasiidui" },
};
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const para = (t) => `<p style="margin:0 0 16px;font-family:${F.sans};font-size:16px;line-height:1.55;color:${C.pine}">${esc(t).replace(/\n/g, "<br>")}</p>`;
const button = (href, label) => `<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:8px 0 24px"><tr>` +
  `<td bgcolor="${C.gold}" style="border-radius:6px;background:${C.gold}"><a href="${esc(href)}" style="display:inline-block;padding:16px 32px;font-family:${F.sans};font-size:18px;font-weight:700;color:${C.pine};text-decoration:none;border-radius:6px">${esc(label)} &rarr;</a></td></tr></table>`;
const linkLine = (lang, href) => `<p style="margin:0 0 20px;font-family:${F.sans};font-size:13px;color:${C.sea}">${esc((B[lang] || B.en).alt)}<br>` +
  `<a href="${esc(href)}" style="font-family:${F.mono};font-size:12px;color:${C.sea};word-break:break-all">${esc(href)}</a></p>`;

export function emailHtml(site, lang, { title, body, link, cta }) {
  const s = SITES[site], home = s.base + (s.langs[lang] ?? ""), b = B[lang] || B.en;
  // Split the plain body: the bare link line becomes the button (or link block), the "{name} – {site}" sign-off goes to the footer.
  const blocks = body.trim().split(/\n\n+/).filter((p) => !p.startsWith(s.name + " – "));
  const inner = blocks.map((p) => {
    if (p.trim() === link) return cta ? button(link, b.btn) + linkLine(lang, link) : "";
    if (p.includes("\n" + link)) return para(p.replace("\n" + link, "")) + (cta ? "" : linkLine(lang, link).replace(esc(b.alt) + "<br>", ""));
    return para(p);
  }).join("");
  return `<!doctype html><html lang="${esc(lang)}"${dir(lang)}><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">` +
    `<meta name="color-scheme" content="light"><title>${esc(title)}</title></head>` +
    `<body style="margin:0;padding:0;background:${C.sail}">` +
    `<div style="display:none;max-height:0;overflow:hidden">${esc(title)}</div>` +
    `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="${C.sail}" style="background:${C.sail}"><tr><td align="center" style="padding:24px 12px">` +
    `<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;background:#ffffff;border:1px solid ${C.foam};border-radius:8px;overflow:hidden">` +
    // North Sea band with logo + wordmark
    `<tr><td bgcolor="${C.sea}" style="background:${C.sea};padding:22px 28px;border-bottom:4px solid ${C.gold}">` +
    `<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>` +
    `<td style="padding-right:14px"><img src="${esc(LOGO)}" width="48" height="48" alt="" style="display:block;border:0"></td>` +
    `<td><div style="font-family:${F.serif};font-size:28px;font-weight:600;line-height:1;color:${C.sail}">${esc(s.name)}</div>` +
    `<div style="font-family:${F.mono};font-size:11px;letter-spacing:2px;text-transform:uppercase;color:${C.gold};padding-top:6px">Newsletter</div></td>` +
    `</tr></table></td></tr>` +
    `<tr><td style="padding:32px 28px 8px">` +
    `<h1 style="margin:0 0 20px;font-family:${F.serif};font-size:30px;line-height:1.15;font-weight:600;color:${C.pine}">${esc(title)}</h1>` +
    inner + `</td></tr>` +
    `<tr><td style="padding:0 28px"><div style="border-top:1px solid ${C.foam};font-size:0;line-height:0">&nbsp;</div></td></tr>` +
    `<tr><td style="padding:18px 28px 26px;font-family:${F.mono};font-size:12px;color:${C.sea}">` +
    `${esc(s.name)} &middot; <a href="${esc(home)}" style="color:${C.sea}">${esc(b.visit)}</a></td></tr>` +
    `</table></td></tr></table></body></html>`;
}
