#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
يبني معاينة HTML ثابتة من ملف القالب dahsha-muthaqa.xml:
- يستخرج CSS من <b:skin> ويستبدل متغيّرات بلوجر $(name) بقيمها.
- يستخرج CSS من <b:template-skin>. (لا يُستخدم في المعاينة)
- ينتج preview/index.html (الرئيسية) و preview/post.html (صفحة مشاركة) بمحتوى عربي تجريبي
  بنفس أصناف (classes) القالب حتى تكون المعاينة مطابقة للتصميم الحقيقي.

الاستخدام:  python3 tools/build-preview.py
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XML = os.path.join(ROOT, 'dahsha-muthaqa.xml')
OUT = os.path.join(ROOT, 'preview')


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def build_css(xml):
    """يستخرج CSS من b:skin ويستبدل متغيّرات بلوجر $(name) بقيمها."""
    skin = re.search(r'<b:skin[^>]*><!\[CDATA\[(.*?)\]\]></b:skin>', xml, re.S).group(1)
    values = {}
    raw = {}
    for tag in re.findall(r'<Variable\b[^>]*/>', skin):
        name = re.search(r'name="([^"]+)"', tag).group(1)
        val = re.search(r'value="([^"]*)"', tag)
        raw[name] = (val.group(1) if val else '', tag)
    for name, (val, tag) in raw.items():
        is_bg = 'type="background"' in tag
        if is_bg:
            color_attr = re.search(r'\scolor="([^"]*)"', tag)
            if color_attr:
                ref = color_attr.group(1)
                if ref.startswith('$(') and ref.endswith(')'):
                    ref = raw.get(ref[2:-1], ('', ''))[0]
                val = val.replace('$(color)', ref)
        values[name] = val

    def font_parts(shorthand):
        toks = shorthand.split()
        size, family, weight = '16px', shorthand, '400'
        for i, t in enumerate(toks):
            if re.match(r'^[\d.]+(px|em|rem|pt|%)$', t):
                size = t
                family = ' '.join(toks[i + 1:]) or shorthand
                if i and re.match(r'^\d{3}$', toks[i - 1]):
                    weight = toks[i - 1]
                break
        return size, family, weight

    def resolve_name(key):
        key = key.strip()
        if key in values:
            return values[key]
        best = None
        for name in values:
            if key.startswith(name + '.') and (best is None or len(name) > len(best)):
                best = name
        if best:
            suffix = key[len(best) + 1:]
            size, family, weight = font_parts(values[best])
            if suffix == 'family':
                return family
            if suffix == 'size':
                return size
            if suffix == 'weight':
                return weight
            if suffix == 'color':
                return values[best]
            return values[best]
        return None

    def expr_sub(m):
        content = m.group(1)
        if not re.search(r'[*/+\-]', content):
            out = resolve_name(content)
            return out if out is not None else m.group(0)
        def tok(mm):
            v = resolve_name(mm.group(0))
            if v is None:
                return mm.group(0)
            v = v.strip()
            return v.replace('px', '') if re.match(r'^[\d.]+px$', v) else v
        try:
            e = re.sub(r'[A-Za-z][A-Za-z0-9_.]*', tok, content)
            return str(round(eval(e, {'__builtins__': {}}, {}), 3)) + 'px'
        except Exception:
            return m.group(0)

    css = re.sub(r'\$\(([^()]*)\)', expr_sub, skin)
    # $(color) داخل تعريف متغيّر الخلفية = لون ذلك المتغيّر
    css = css.replace('$(color)', values.get('header.background.color', '#ffffff'))
    return css


HOME_BODY = """
<a class='skip-link' href='#main'>تخطَّ إلى المحتوى</a>

<header class='site-header' id='page-top'>
  <div class='container header-inner'>
    <div class='header-widget'>
      <h1 class='site-title'><a href='index.html'>دهشة موثّقة</a></h1>
      <p class='site-description'>خواطر ومقالات في الأدب والفكر وتفاصيل الجمال اليومي</p>
      <div class='header-ornament'>
        <svg class='ornament-diamond' height='9' viewBox='0 0 10 10' width='9'><path d='M5 0 10 5 5 10 0 5z'/></svg>
      </div>
    </div>
  </div>

  <nav class='site-nav'>
    <div class='container nav-inner'>
      <input class='nav-toggle-checkbox' id='nav-toggle' type='checkbox'/>
      <label class='nav-toggle' for='nav-toggle' title='القائمة'>
        <svg class='icon-menu' height='22' viewBox='0 0 24 24' width='22'><path d='M3 6h18M3 12h18M3 18h18'/></svg>
        <svg class='icon-close' height='22' viewBox='0 0 24 24' width='22'><path d='M6 6l12 12M18 6L6 18'/></svg>
      </label>
      <div class='nav-menu section'>
        <div class='widget PageList'><div class='widget-content'>
          <ul>
            <li class='selected'><a href='index.html'>الرئيسية</a></li>
            <li><a href='#'>عن المدونة</a></li>
            <li><a href='#'>مراجعات الكتب</a></li>
            <li><a href='post.html'>مقالة مفردة</a></li>
            <li><a href='#'>اتصل بنا</a></li>
          </ul>
        </div></div>
      </div>
      <form class='nav-search' role='search' onsubmit='return false'>
        <button aria-label='ابحث' type='submit'>
          <svg height='17' viewBox='0 0 24 24' width='17'><circle cx='11' cy='11' r='7'/><path d='M20 20l-3.6-3.6'/></svg>
        </button>
        <input aria-label='ابحث في هذه المدونة' autocomplete='off' placeholder='ابحث في المدونة...' type='search'/>
        <span class='search-hint'>اضغط Enter للبحث</span>
      </form>
    </div>
  </nav>
</header>

<div class='site-main'>
  <div class='container layout-grid'>
    <main class='content-area' id='main'>
      <div class='post-feed'>
        {CARDS}
      </div>
      <nav class='blog-pager'>
        <a href='#'>رسائل أحدث</a>
        <a href='#'>رسائل أقدم</a>
      </nav>
    </main>
    <aside class='sidebar'>
      {SIDEBAR}
    </aside>
  </div>
</div>
"""


def card(img, labels, title, author, date, comments, snippet, href='post.html', no_thumb=False):
    thumb = ''
    if not no_thumb:
        thumb = ("<a class='post-thumb' href='{href}'><img alt='' loading='lazy' src='{img}'/></a>").format(href=href, img=img)
    return """
<article class='post-card{class_no_thumb}'>
  {thumb}
  <div class='post-body-wrap'>
    <div class='post-labels'>{labels}</div>
    <h2 class='entry-title'><a href='{href}'>{title}</a></h2>
    <div class='post-meta'>
      <span class='meta-author'>
        <svg height='15' viewBox='0 0 24 24' width='15'><circle cx='12' cy='8' r='4'/><path d='M4 21c0-4 3.6-6.4 8-6.4s8 2.4 8 6.4'/></svg>
        {author}
      </span>
      <span class='meta-date'>
        <svg height='15' viewBox='0 0 24 24' width='15'><circle cx='12' cy='12' r='9'/><path d='M12 7v5.2l3 2'/></svg>
        <time>{date}</time>
      </span>
      <a class='meta-comments' href='{href}#comments'>
        <svg height='15' viewBox='0 0 24 24' width='15'><path d='M21 12a8 8 0 0 1-8 8H7l-4 3v-5.2A8 8 0 0 1 11 4h2a8 8 0 0 1 8 8z'/></svg>
        {comments}
      </a>
    </div>
    <div class='post-snippet'><p>{snippet}</p></div>
    <a class='read-more' href='{href}'>اقرأ المزيد</a>
  </div>
</article>""".format(
        class_no_thumb=' no-thumb' if no_thumb else '',
        thumb=thumb,
        labels=''.join("<a href='#'>{0}</a>".format(l) for l in labels),
        title=title, author=author, date=date, comments=comments, snippet=snippet, href=href)


SIDEBAR = """
<div class='widget Profile'>
  <h2 class='widget-title'><span>من أنا</span></h2>
  <div class='widget-content'>
    <a class='profile-image-link' href='#'>
      <img class='profile-img' alt='صورتي' src='https://picsum.photos/seed/dahsha-me/208/208'/>
    </a>
    <div class='profile-name'>دهشة موثّقة</div>
    <div class='profile-textblock'>أكتب عن الكتب والمدن والحكايات الصغيرة التي تستحق أن تُروى.</div>
    <a class='profile-link visit-profile' href='#'>زيارة الملف الشخصي</a>
  </div>
</div>

<div class='widget PopularPosts'>
  <h2 class='widget-title'><span>الأكثر قراءة</span></h2>
  <div class='widget-content'>
    <div class='popular-item'>
      <a class='item-thumbnail' href='post.html'><img loading='lazy' src='https://picsum.photos/seed/dahsha-p1/170/170' alt=''/></a>
      <div class='item-content'>
        <h3 class='item-title'><a href='post.html'>حكاية الروائي الذي كره الحواشي</a></h3>
        <div class='item-meta'>١٢ أغسطس ٢٠٢٦</div>
      </div>
    </div>
    <div class='popular-item'>
      <a class='item-thumbnail' href='post.html'><img loading='lazy' src='https://picsum.photos/seed/dahsha-p2/170/170' alt=''/></a>
      <div class='item-content'>
        <h3 class='item-title'><a href='post.html'>في مدح المكتبات القديمة</a></h3>
        <div class='item-meta'>٣ يوليو ٢٠٢٦</div>
      </div>
    </div>
    <div class='popular-item'>
      <div class='item-number'>3</div>
      <div class='item-content'>
        <h3 class='item-title'><a href='post.html'>عن الفهارس، وذاكرة الكتب</a></h3>
        <div class='item-meta'>٢١ يونيو ٢٠٢٦</div>
      </div>
    </div>
  </div>
</div>

<div class='widget Label'>
  <h2 class='widget-title'><span>التسميات</span></h2>
  <div class='widget-content'>
    <ul class='label-list'>
      <li><a href='#'>أدب</a><span class='label-count'>12</span></li>
      <li><a href='#'>مراجعات</a><span class='label-count'>9</span></li>
      <li><a href='#'>تاريخ</a><span class='label-count'>7</span></li>
      <li><a href='#'>فنون</a><span class='label-count'>5</span></li>
      <li><a href='#'>خواطر</a><span class='label-count'>4</span></li>
    </ul>
  </div>
</div>

<div class='widget BlogArchive'>
  <h2 class='widget-title'><span>الأرشيف</span></h2>
  <div class='widget-content'>
    <ul class='archive-list'>
      <li><a href='#'>أغسطس ٢٠٢٦</a><span class='post-count'>6</span></li>
      <li><a href='#'>يوليو ٢٠٢٦</a><span class='post-count'>8</span></li>
      <li><a href='#'>يونيو ٢٠٢٦</a><span class='post-count'>5</span></li>
    </ul>
  </div>
</div>
"""

FOOTER = """
<footer class='site-footer' id='footer'>
  <div class='container'>
    <div class='footer-widgets'>
      <div class='widget HTML'>
        <h2 class='widget-title'><span>عن المدونة</span></h2>
        <div class='widget-content'>
          <p>مدونة شخصية تُعنى بالأدب والكتب والتفاصيل الجميلة، بخطّ نسخيّ هادئ ولون ذهبيّ كلاسيكي.</p>
        </div>
      </div>
      <div class='widget Label'>
        <h2 class='widget-title'><span>تسميات مختارة</span></h2>
        <div class='widget-content'>
          <ul class='label-list'>
            <li><a href='#'>أدب</a></li>
            <li><a href='#'>مراجعات</a></li>
            <li><a href='#'>فنون</a></li>
            <li><a href='#'>تاريخ</a></li>
          </ul>
        </div>
      </div>
      <div class='widget LinkList'>
        <h2 class='widget-title'><span>روابط</span></h2>
        <div class='widget-content'>
          <ul>
            <li><a href='#'>عن المدونة</a></li>
            <li><a href='#'>سياسة الخصوصية</a></li>
            <li><a href='#'>خريطة الموقع</a></li>
            <li><a href='#'>اتصل بنا</a></li>
          </ul>
        </div>
      </div>
    </div>
  </div>
  <div class='footer-bottom'>
    <div class='container'>
      <div class='footer-note'>دهشة موثّقة © <span class='dahsha-year'>2026</span> — جميع الحقوق محفوظة</div>
      <div class='widget Attribution'>
        <div class='widget-content'>
          <div class='blogger'><a href='#' rel='nofollow'>مدعوم بواسطة Blogger</a></div>
        </div>
      </div>
    </div>
  </div>
</footer>

<a class='to-top is-hidden' href='#page-top' title='إلى أعلى الصفحة'>
  <svg height='20' viewBox='0 0 24 24' width='20'><path d='M12 19V5M5 12l7-7 7 7'/></svg>
</a>
<script>
(function(){
  document.querySelectorAll('.dahsha-year').forEach(function(e){e.textContent=new Date().getFullYear();});
  var t=document.querySelector('.to-top');
  if(t){var u=function(){window.scrollY>420?t.classList.remove('is-hidden'):t.classList.add('is-hidden');};
  window.addEventListener('scroll',u,{passive:true});u();}
})();
</script>
</body>
</html>
"""

POST_BODY = """
<a class='skip-link' href='#main'>تخطَّ إلى المحتوى</a>
<header class='site-header' id='page-top'>
  <div class='container header-inner'>
    <div class='header-widget'>
      <p class='site-title'><a href='index.html'>دهشة موثّقة</a></p>
      <p class='site-description'>خواطر ومقالات في الأدب والفكر وتفاصيل الجمال اليومي</p>
      <div class='header-ornament'>
        <svg class='ornament-diamond' height='9' viewBox='0 0 10 10' width='9'><path d='M5 0 10 5 5 10 0 5z'/></svg>
      </div>
    </div>
  </div>
  <nav class='site-nav'>
    <div class='container nav-inner'>
      <div class='nav-menu section'>
        <div class='widget PageList'><div class='widget-content'>
          <ul>
            <li><a href='index.html'>الرئيسية</a></li>
            <li class='selected'><a href='post.html'>مقالة مفردة</a></li>
            <li><a href='#'>عن المدونة</a></li>
          </ul>
        </div></div>
      <form class='nav-search' role='search' onsubmit='return false'>
        <button aria-label='ابحث' type='submit'>
          <svg height='17' viewBox='0 0 24 24' width='17'><circle cx='11' cy='11' r='7'/><path d='M20 20l-3.6-3.6'/></svg>
        </button>
        <input aria-label='ابحث في هذه المدونة' autocomplete='off' placeholder='ابحث في المدونة...' type='search'/>
        <span class='search-hint'>اضغط Enter للبحث</span>
      </form>
    </div>
  </nav>
</header>

<div class='site-main'>
  <div class='container layout-grid'>
    <main class='content-area' id='main'>
      <article class='entry'>
        <div class='post-labels'><a href='#'>أدب</a><a href='#'>مراجعات</a></div>
        <header class='entry-header'>
          <h1 class='entry-title'>حكاية الروائي الذي كره الحواشي</h1>
          <div class='post-meta'>
            <span class='meta-author'>
              <svg height='15' viewBox='0 0 24 24' width='15'><circle cx='12' cy='8' r='4'/><path d='M4 21c0-4 3.6-6.4 8-6.4s8 2.4 8 6.4'/></svg>
              دهشة موثّقة
            </span>
            <span class='meta-date'>
              <svg height='15' viewBox='0 0 24 24' width='15'><circle cx='12' cy='12' r='9'/><path d='M12 7v5.2l3 2'/></svg>
              <time>١٢ أغسطس ٢٠٢٦</time>
            </span>
            <a class='meta-comments' href='#comments'>
              <svg height='15' viewBox='0 0 24 24' width='15'><path d='M21 12a8 8 0 0 1-8 8H7l-4 3v-5.2A8 8 0 0 1 11 4h2a8 8 0 0 1 8 8z'/></svg>
              ٣ تعليقات
            </a>
          </div>
          <div class='entry-divider'>
            <svg class='ornament-diamond' height='9' viewBox='0 0 10 10' width='9'><path d='M5 0 10 5 5 10 0 5z'/></svg>
          </div>
        </header>
        <div class='entry-content'>
          <img alt='' src='https://picsum.photos/seed/dahsha-hero/1200/700'/>
          <p>هناك روايات تُقرأ مرة واحدة، وهناك روايات تعود إليك في الحواشي؛ في تلك المساحة الصغيرة أسفل
          الصفحة حيث يترك الكاتب صوتًا خفيًّا، همسًا لا يُقال في المتن. عن هذا الهمس كانت الحكاية.</p>
          <h2>الحاشية كصوت ثانٍ</h2>
          <p>كان يقول إن الحاشية ليست شرحًا، بل غرفة صغيرة يدخلها القارئ ليجد الكاتب جالسًا وحده، بلا قناع
          السرد ولا سلطة العنوان. ثمة اعترافات لا تُكتب إلا هناك.</p>
          <blockquote>«الكتاب الذي لا حاشية فيه كتابٌ صامت؛ يحدّثك ولا يبوح لك».</blockquote>
          <h3>ثلاث ملاحظات على الهامش</h3>
          <ul>
            <li>الحاشية تمنح القارئ مساحة للمقاومة، لا للطاعة.</li>
            <li>في الحاشية يتساوى المؤلف مع مترجمه.</li>
            <li>أجمل الحواشي تلك التي تفتح سؤالًا وتغلق صفحة.</li>
          </ul>
          <p>ثم أضاف، وهو يقلّب كتابًا قديمًا: <a href='#'>اقرأ الحواشي أولًا</a>، فالمتن يصبر عليك،
          أما الحاشية فقد لا تعود.</p>
          <pre><code>// هكذا تبدو الحاشية في كتابٍ رقمي
note = { page: 214, voice: "whisper" }</code></pre>
          <table>
            <thead><tr><th>الطبعة</th><th>السنة</th><th>عدد الصفحات</th></tr></thead>
            <tbody>
              <tr><td>الأولى</td><td>1987</td><td>312</td></tr>
              <tr><td>الثانية</td><td>2004</td><td>348</td></tr>
            </tbody>
          </table>
          <p>وبعد سنوات، وجدتُ نسختَه الشخصية في مكتبة مستعملة؛ الحواشي فيها بخطّه، والمتن بأيدٍ أخرى.
          عند الصفحة 214 كان هناك وسم ذهبيّ صغير، وتحته سطر واحد: «هنا تبدأ الرواية الحقيقية».</p>
        </div>

        <div class='entry-labels'>
          <span class='labels-title'>التسميات:</span>
          <a href='#'>أدب</a><a href='#'>مراجعات</a><a href='#'>قراءات</a>
        </div>

        <div class='share-box'>
          <div class='share-title'>شارك هذه المشاركة</div>
          <ul class='share-list'>
            <li><a href='#'>فيسبوك</a></li>
            <li><a href='#'>إكس</a></li>
            <li><a href='#'>واتساب</a></li>
            <li><a href='#'>تيليجرام</a></li>
            <li><a href='#'>بينترست</a></li>
            <li><a href='#'>لينكدإن</a></li>
            <li><a href='#'>البريد</a></li>
          </ul>
        </div>

        <div class='author-box'>
          <img alt='' src='https://picsum.photos/seed/dahsha-author/160/160'/>
          <div class='author-info'>
            <div class='author-name'>دهشة موثّقة</div>
            <p class='author-about'>أكتب عن الكتب والمدن والحكايات الصغيرة التي تستحق أن تُروى، وأظلّ وفيًّا للحواشي.</p>
          </div>
        </div>
      </article>

      <nav class='post-pager'>
        <a class='pager-newer' href='#'><span class='pager-label'>المشاركة السابقة</span>في مدح المكتبات القديمة</a>
        <a class='next pager-older' href='#'><span class='pager-label'>المشاركة التالية</span>عن الفهارس، وذاكرة الكتب</a>
      </nav>

      <section class='comments threaded' id='comments'>
        <h3 class='comments-title'>التعليقات</h3>
        <div class='comments-content'>
          <div id='comment-holder'>
            <div class='comment'>
              <div class='comment-block'>
                <div class='comment-header'>
                  <div class='avatar-image-container'><img class='author-avatar' src='https://picsum.photos/seed/dahsha-c1/84/84' alt=''/></div>
                  <div class='comment-info'>
                    <div class='comment-author'><a href='#'>سالم العتيبي</a> قال...</div>
                    <span class='datetime'><a href='#'>١٣ أغسطس ٢٠٢٦، ٩:٤١ ص</a></span>
                  </div>
                </div>
                <div class='comment-content'><p>«الحاشية غرفة صغيرة يدخلها القارئ» — هذه الجملة وحدها تستحق مقالًا. شكرًا لك.</p></div>
              </div>
              <div class='comment-replies'>
                <div class='comment'>
                  <div class='comment-block'>
                    <div class='comment-header'>
                      <div class='avatar-image-container'><img class='author-avatar' src='https://picsum.photos/seed/dahsha-c2/84/84' alt=''/></div>
                      <div class='comment-info'>
                        <div class='comment-author'><a href='#'>دهشة موثّقة</a> قال...</div>
                        <span class='datetime'><a href='#'>١٣ أغسطس ٢٠٢٦، ١١:٠٢ ص</a></span>
                      </div>
                    </div>
                    <div class='comment-content'><p>شكرًا سالم، وسيبقى للهوامش نصيب من الكتابة القادمة.</p></div>
                  </div>
                </div>
              </div>
            </div>
            <div class='comment'>
              <div class='comment-block'>
                <div class='comment-header'>
                  <div class='avatar-image-container'><img class='author-avatar' src='https://picsum.photos/seed/dahsha-c3/84/84' alt=''/></div>
                  <div class='comment-info'>
                    <div class='comment-author'><a href='#'>مريم</a> قالت...</div>
                    <span class='datetime'><a href='#'>١٤ أغسطس ٢٠٢٦، ٧:١٥ م</a></span>
                  </div>
                </div>
                <div class='comment-content'><p>قرأتها ثم عدت إلى روايتي القديمة أبحث عن حواشيها. فعلت بي شيئًا جميلًا.</p></div>
              </div>
            </div>
          </div>
        </div>
        <p class='comment-footer'>
          <div class='comment-form'>
            <h4>أضف تعليقًا</h4>
            <div class='blogger-iframe-colorize' style='border:1px dashed #e8e1d5;padding:32px;text-align:center;color:#8c8578'>
              نموذج تعليقات بلوجر يظهر هنا (نظام التعليقات المتشابكة)
            </div>
          </div>
        </p>
      </section>
    </main>
    <aside class='sidebar'>
      {SIDEBAR}
    </aside>
  </div>
</div>
"""


def page(title, body_inner):
    return """<!DOCTYPE html>
<html dir='rtl' lang='ar'>
<head>
<meta charset='UTF-8'/>
<meta content='width=device-width, initial-scale=1' name='viewport'/>
<title>{title}</title>
<link href='https://fonts.googleapis.com' rel='preconnect'/>
<link crossorigin='anonymous' href='https://fonts.gstatic.com' rel='preconnect'/>
<link href='https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400&amp;family=Almarai:wght@300;400;700;800&amp;display=swap' rel='stylesheet'/>
<style>
/* ====== هذه المعاينة تُبنى آليًّا من ملف القالب dahsha-muthaqa.xml (نفس CSS) ====== */
{CSS}
</style>
</head>
<body>
{body}
""".format(title=title, CSS='__CSS__', body=body_inner)


def main():
    xml = read(XML)
    css = build_css(xml)
    os.makedirs(OUT, exist_ok=True)

    cards = [
        card('https://picsum.photos/seed/dahsha-a/800/600', ['أدب', 'قراءات'],
             'حكاية الروائي الذي كره الحواشي', 'دهشة موثّقة', '١٢ أغسطس ٢٠٢٦', '٣ تعليقات',
             'في المساحة الصغيرة أسفل الصفحة يترك الكاتب صوتًا خفيًّا، همسًا لا يُقال في المتن؛ عن هذا الهمس كانت الحكاية.'),
        card('https://picsum.photos/seed/dahsha-b/800/600', ['فنون'],
             'في مدح المكتبات القديمة', 'دهشة موثّقة', '٣ يوليو ٢٠٢٦', 'تعليقان',
             'رائحة الورق القديم ليست تفصيلًا عابرًا، بل ذاكرة كاملة تفتح أبوابها كلما اقتربت من الرفّ الثالث.'),
        card('https://picsum.photos/seed/dahsha-c/800/600', ['تاريخ'],
             'عن الفهارس، وذاكرة الكتب', 'دهشة موثّقة', '٢١ يونيو ٢٠٢٦', 'أضف تعليقًا',
             'الفهرس هو الخريطة التي لا يكترث لها أحد، ومع ذلك بها يهتدي القارئ إلى ما لا يتوقّعه.'),
        card('', ['خواطر'],
             'رسالة قصيرة إلى من يقرأ في المقهى', 'دهشة موثّقة', '٩ يونيو ٢٠٢٦', '٥ تعليقات',
             'لا شيء أجمل من قارئ ينسى قهوته وهو يتقدّم في فصلٍ لم يخطّط له.', no_thumb=True),
    ]

    home_body = HOME_BODY.replace('{CARDS}', '\n'.join(cards)).replace('{SIDEBAR}', SIDEBAR)
    home = page('دهشة موثّقة', home_body + FOOTER).replace('__CSS__', css)
    post_body = POST_BODY.replace('{SIDEBAR}', SIDEBAR)
    post = page('حكاية الروائي الذي كره الحواشي — دهشة موثّقة', post_body + FOOTER).replace('__CSS__', css)

    pages = [('index.html', home), ('post.html', post)]
    for name, html in pages:
        with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
            f.write(html)
        print('wrote', os.path.join('preview', name), len(html), 'bytes')


if __name__ == '__main__':
    main()
