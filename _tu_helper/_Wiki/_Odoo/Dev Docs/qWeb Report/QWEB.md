Module 5. Reports and qWeb 
1. Синтаксис
1) QWeb що це таке?

QWeb є основним механізмом шаблонів , який використовується в Odoo. Можливо, ви вже знайомі з існуючими механізмами, такими як Jinja (Python), ERB (Ruby) або Twig (PHP). Odoo постачається з власним вбудованим двигуном: QWeb Templates. Це механізм шаблонів XML , який використовується в основному для створення звітів і сторінок HTML.

Процесор шаблонів (також відомий як механізм шаблонів або синтаксичний аналізатор шаблонів ) — це програмне забезпечення , призначене для поєднання шаблонів з моделлю даних і створення документів.

В шаблонах Odoo за замовчуванням використовуються основні технології HTML конструкції та  комбінація Js і CSS
Шаблон створюється в XML файлі який потім парситься і відтворюється в HTML відображенні, HTML конструкції не підаються перетворенню, перетворюються Odoo атрибути які ми розглянемо далі у наших уроках.

2) Використання шаблону в Odoo.
Звіти
Звіти використовуються в більшості ключових моделей (звіти по продуктам, замовленням, рахункам і т.д.)
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Звіти.png
 
 
Сторінки
Сторінка використовується для Odoo сайту і таких його ф-цій як магазин, покупка товарів, POS термінал та інше. 
 Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Сторінки.png
Канбан
Це гнучке відображення корисної інформації в виді який найкраще пдходить для веб відображення на мобільних девайсах
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Канбан.png

 
Листи
Шаблони листів використовуються для автоматизації форми створення електронних листів для клієнтів, співробітників або партнерів компаніїї
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Листи.png
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Листи1.png
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Листи2.png

 

 

 
 

Використання Шаблонів різноманітне і охоплює велику кількість функцій які реалізовані в Odoo. В цьому курсі детальніше будемо розглядати найчастіше використовувані види Звіт і Канбан. 
3) Структура базового шаблону.
Будь-який файл Odoo XML починається зі <odoo>тегу.
<odoo>
   ## YOUR CODE HERE
</odoo>

Майже кожен елемент і параметр QWeb шаблону, які ви створюєте, потрібно помістити в <template>тег, як у цьому прикладі.

<template id="my_title" name="My title">
<h1>This is an HTML block</h1>
<h2 class="lead">And this is a subtitle</h2>
</template>

Розглянемо детальніше:
Тегу <template/> присвоєно унікальний ідентифікатор id="my_title" і ім’я name="My title", ці атрибути тега використовуються для виклика та унаслідування шаблонів і є обов'язковими при створенні шаблону, як їх використовувати розглянемо в Уроці 36. Всередині тегу два стандартні HTML заголовки.

Як видно синтаксис QWeb шаблону схожий до HTML і використовує більшість його конструкцій та доповнює атрибутами XML, які ми розглянемо в наступних уроках цього модуля.

4) Практична частина - створення модуля і відображення базового шаблона.

====================================================
Создать файлы и Прописать их в матифесте в разделе 'data'
====================================================

  'data': [
        'report/hr_hospital_doctor_report.xml',
        'report/hr_hospital_doctor_reports_template.xml',
    ],
====================================================
Содержание файла 'report/hr_hospital_doctor_report.xml
====================================================
<odoo>
    <data>
        <record id="paperformat_lowmargin" model="report.paperformat">
            <field name="name">European A4 low margin</field>
            <field name="default" eval="True"/>
            <field name="format">A4</field>
            <field name="page_height">0</field>
            <field name="page_width">0</field>
            <field name="orientation">Portrait</field>
            <field name="margin_top">1</field>
            <field name="margin_bottom">1</field>
            <field name="margin_left">1</field>
            <field name="margin_right">1</field>
            <field name="header_line" eval="False"/>
            <field name="header_spacing">0</field>
            <field name="dpi">90</field>
        </record>

       <report
            id="action_report_doctor"
            string="Doctor Report"
            model="hr_hospital.doctor"
            report_type="qweb-pdf"
            file="hr_hospital.report_doctor"
            name="hr_hospital.report_doctor"
            paperformat="paperformat_lowmargin"
            print_report_name="'Doctor - %s' % (object.name)"
        />


    </data>
</odoo>

Обратить внимание на строки
            file="hr_hospital.report_doctor"
            name="hr_hospital.report_doctor"
            должны ссылаться на <template id=" report_doctor "> в файле hr_hospital_doctor_reports_template

====================================================
Содержание файла 'report/ hr_hospital_doctor_reports_template.xml
====================================================

<odoo>
    <template id=" report_doctor ">
        <t t-call="web.html_container">
            <h1> hello World</h1>
        </t>
    </template>
</odoo>



2. Умови і цикли
Умови t-if, t-elif, t-else

Директиви шаблону вказуються як атрибути XML із префіксом t-, наприклад t-if для умовних , з елементами та іншими атрибутами, які відображаються безпосередньо.
Розглянемо умовний атрибут t-if, атрибут має вигляд

<t t-if="condition">

 	<p>Test</p>

</t>

Результатом буде 
<p>Test</p>

Але якщо замість тега t буде тег div результат буде
<div>
<p>Test</p>
</div>

Атрибут може використовуватись і з іншими тегами окрім t
<span t-if=””>...</span>

<div t-if=””>...</div>

<p t-if=””>...</p>

<img t-if=””/>

Цикли t-foreach .. t-as

Розглянемо умовний атрибут t-foreach, атрибут має вигляд
<t t-foreach="[1, 2, 3]" t-as="i">

<p><t t-out="i"/></p>

</t>
Результатом буде 

<p>1</p>
<p>2</p>
<p>3</p>


Атрибут може використовуватись і з іншими тегами окрім t
<tr t-if=””>...</tr>

<ul t-if=””>...</ul>


Таблицы
 Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Таблицы.png
 
3) Додаткові змінні t-foreach

На додаток до імені, переданого через t-as, foreach надає кілька інших змінних для різних даних:
 Увага
$as буде замінено на ім’я, кому передано t-as

$as_value
поточне значення ітерації, ідентичне $as для списків і цілих чисел, але для відображень воно надає значення (де $as надає ключ)
$as_index
поточний індекс ітерації (перший елемент ітерації має індекс 0)
$as_size
розмір колекції, якщо вона доступна
$as_first
чи є поточний елемент першим із ітерації (еквівалентно ) $as_index == 0
$as_last
чи є поточний елемент останнім з ітерації (еквівалент ), вимагає наявності розміру повторюваного $as_index + 1 == $as_size 
Ці додаткові надані змінні та всі нові змінні, створені в foreach файлі, доступні лише в області дії foreach. Якщо змінна існує поза контекстом foreach, значення копіюється в кінці foreach у глобальний контекст.


4) Приклади використання в Odoo

	<table t-foreach …

 

 
 
	<div t-foreach  …

 

 

 







	<tr t-foreach  …

 

 

 

	<ul t-foreach  …

 




3. Виведення даних

t-out

Вихідна директива QWeb out буде автоматично виходити з HTML, що обмежує ризики Cross-site scripting (XSS) під час відображення вмісту, наданого користувачем.
out приймає вираз, оцінює його та вводить результат у документ:
<p><t t-out="value"/></p>

відображається зі значенням value, встановленим на 42:
<p>42</p>
t-field

t-field  можна використовувати лише під час виконання доступу до поля (Робота лише зі збереженими полями) та форматування даних відповідно до типу поля. 
Крім того,  t-field-options  можна використовувати для налаштування полів., 

<t t-field="company.date" t-field-options='{"widget":"date"}'/>

<t t-set="doc" t-value="doc.with_context(lang=doc.partner_id.lang)" />

<t t-set="address">
    <div t-field="doc.partner_id"
        t-options='{"widget": "contact", "fields": ["address", "name"], "no_marker": True}' />
    <p t-if="doc.partner_id.vat'><t t-esc="doc.company_id.account_fiscal_country_id.vat_label or 'Tax ID'"/>: <span t-field="doc.partner_id.vat"/></p>
</t>

 

 



t-esc

t-esc дозволяє вам оцінити код, як код Python, і роздрукувати його. 
<t t-esc="dict['key']"/>

            <span t-esc="doc.author_id.get_full_name()"/>

Приклади використання в Odoo


4. Змінні

1.	Встановлення змінних t-set … t-value, <t t-set=...></t>
2.	Приклади використання в Odoo
3.	Практична частина - розширення базового шаблону

1) Встановлення змінних t-set … t-value, <t t-set=...></t>

QWeb дозволяє створювати змінні всередині шаблону, запам’ятовувати обчислення (використовувати його кілька разів), дати фрагменту даних більш чітке ім’я, …
Це робиться за допомогою set директиви, яка приймає ім’я створюваної змінної. Встановлене значення можна надати двома способами:
атрибут , t-value що містить вираз, і буде встановлено результат його оцінки:

<t t-set="foo" t-value="2 + 1"/>

<t t-out="foo"/>

Надрукує -  3
якщо атрибута немає t-value, тіло вузла відображається і встановлюється як значення змінної:

<t t-set="foo">

<li>ok</li>

</t>

<t t-out="foo"/>

Приклади

<t t-set="title">Company Data</t>


<t t-set="record" t-value="object.env['crm.team'].search([('alias_name', '!=', 'False')], limit=1)" />



5. Вирази і умовні атрибути

1.	Вирази
	18.1 Атрибути об’єктів {{ obj.name }}
	18.2 Дата і час
2.	t-att-$name
3.	t-attf-$name
4.	t-att=mapping
5.	t-att=pair
6.	Приклади використання в Odoo
7.	Практична частина - розширення базового шаблону

1) Вирази
	1.1) Атрибути об’єктів {{ obj.name }}

Атрибути об’єктів моделі в шаблоні визначаються контекстним словником, що передається шаблону.

Ви можете використовувати змінні моделі в шаблонах за умови, що вони передані програмою. Змінні можуть мати атрибути або елементи, до яких ви також можете отримати доступ. Які атрибути має змінна, значною мірою залежить від програми, яка надає цю змінну.

t-attf-href="/web/content/{{item._name}}/{{item.id}}/letter_file"

t-attf-class="cha_move_change_state btn btn-primary btn-state {{item.customs_state == 'goes' and 'active' or ''}}"

<input t-attf-id="quantity_{{i}}" t-attf-name="quantity_{{i}}" type="text" class="form-control" />

<field name="email_to">{{ (not object.partner_id and object.email_from) }}</field>

<img t-attf-src="/logo.png?company={{ object.company_id.id }}" style="padding: 0px; margin: 0px; height: 48px;" t-att-alt="object.company_id.name"/>


	1.2) Дата і час


<field name="date_open" eval="(DateTime.today() - relativedelta(months=1)).strftime('%Y-%m-%d %H:%M')"/>


<field name="end_sale_datetime" eval="(DateTime.today() + timedelta(days=10)).strftime('%Y-%m-%d 23:00:00')"/>

2) t-att-$name

створюється викликаний $name атрибут, оцінюється значення атрибута, а результат встановлюється як значення атрибута:
<div t-att-a="42"/>

буде відображатися як:
<div a="42"></div>



2) t-attf-$name

те саме, що і попередній, але параметр є рядком формату, а не просто виразом, часто корисним для змішування літерного та нелітерального рядка (наприклад, класів):
<t t-foreach="[1, 2, 3]" t-as="item">

   <li t-attf-class="row {{ (item_index % 2 === 0) ? 'even' : 'odd' }}">

       <t t-out="item"/>

   </li>

</t>

буде відображатися як:
<li class="row even">1</li>
<li class="row odd">2</li>
<li class="row even">3</li>

2) t-att=mapping

якщо параметр є відображенням, кожна пара (ключ, значення) генерує новий атрибут і його значення:
<div t-att="{'a': 1, 'b': 2}"/>

буде відображатися як:
<div a="1" b="2"></div>





2) t-att=pair

якщо параметр є парою (кортеж або масив з 2 елементів), першим елементом пари є ім'я атрибута, а другим елементом є значення:
<div t-att="['a', 'b']"/>

буде відображатися як:
<div a="b"></div>


6. Виклик і наслідування шаблонів

1.	Виклик t-call
2.	Стандартні підшаблони модуля web
3.	Наслідування шаблонів
4.	Розширення шаблонів
5.	Практична частина - розширення базового шаблону

1) Виклик t-call

Шаблони QWeb можна використовувати для візуалізації верхнього рівня, але їх також можна використовувати з іншого шаблону (щоб уникнути дублювання або дати імена частинам шаблонів) за допомогою t-call директиви:
<t t-call="other-template"/>

T-call викликає названий шаблон із контекстом виконання батьківського контексту, якщо шаблон визначено як:
<p><t t-value="var"/></p>

наведений вище виклик буде відображатися як <p/>(без вмісту), але:
<t t-set="var" t-value="1"/>

<t t-call="other-template"/>


буде відображатися як <p>1</p>.
Однак це має проблему бути видимим ззовні t-call. Крім того, вміст, установлений у тілі call директиви, буде оцінено перед викликом підшаблону та може змінити локальний контекст:
<t t-call="other-template">
<t t-set="var" t-value="1"/>
</t>
<!-- "var" does not exist here →

Тіло call директиви може бути довільно складним (не тільки set директиви), і його відтворена форма буде доступна у викликаному шаблоні як магічна 0 змінна:
<div>
This template was called with content:
<t t-out="0"/>
</div>


називається так:
<t t-call="other-template">
<em>content</em>
</t>

призведе до:
<div>
   This template was called with content:
   <em>content</em>
</div>

Виклик і наслідування шаблонів з інших модулей які є у системі можливий тільки якщо модуль наслідує модуль в якому розташований цей шаблон в depends в __manifest__.py





2) Стандартні підшаблони модуля web

<t t-call="web.html_container">
Каркас для створення шаблонів
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Каркас для створення шаблонів.png
 <template id="report_laypout" name="Report layout"><!DOCTYPE html>
    <html t-att-lang="lang and lang.replace('_', '-')"
          t-att-data-report-mergin-top="data_report_mergin_top"
          t-att-data-report-header-spacing="data_report_header_spacing"
          t-att-data-report-dpi="data_report_dpi"
          t-att-data-report-landscape="data_report_landscape"
          t-att-web-base-url="web_base_url"
         <head>
            <meta charset="utf-8"/>
            <meta name="viewport" content="initial-scale=1"/>
            <title><t t-esc="title or 'Odoo Report'"/></title>
            <t t-call-assets="web.report_assets_common" t-js="false"/>
            <script type="text/javascript">
                window.odoo = {}
                window.odoo.__session_info__ = {is_report: true};
            </script>
            <t t-call-assets="web.assets_common" t-css="false"/>
            <t t-call-assets="web.report_assets_common" t-css="false"/>
         </head>
         <body t-att-class="'container' if not full_width else 'container-fluid'">
            <div id="wrapwrap">
                <main>
                    <t t-out="0"/>
                </main>
            </div>
         </body>
    </html>
 </template>


<Basic_layuot>
Internal_layout -  використовується для документів всередині компанії
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Internal_layout.png
<template id="internal_layout">
    <t t-if="not o" t-set="o" t-value="doct"/>

    <t t-if="not company">
      <!-- Multicompany -->
      <t t-if="company_id">
          <t t-set="company" t-value="company_id"/>
      </t>
      <t t-elif="o and 'company_id' in 0 nad 0.company_id.sudo()">
          <t t-set="company" t-value="o.company_is.sudo()"/>
      </t>
      <t t-else="else">
        <t t-set="company" t-value="res_company"/>
      </t>
   </t>

   <div class="header">
    <div class="row">
        <div class="col-3">
            <span t-esc="context_timestamp(datetime.datetime.now()).strftime('%Y-%m-%d %H:%M')"/>
        </div>
        <div class="col-2 offset-2 text-center">
            <span t-esc="company.name"/>
        </div>
        </div class="col-2 offset-3 text-right">
            <ul class="list-inline">
                <li class="list-inline-item"><span class="page"/></li>
                <li class="list-inline-item">/</li>
                <li class="list-inline-item"><span class="topage"/></li>
            </ul>
        </div>
      </div>
    </div>
    <div class="article" t-att-data-oe-model="o and o._name" t-att_data_oe-id="o and o.id" t-att-data-oe-lang="o and o.env.context.get('lang')">
        <t t-out="0"/>
    </div>
</template>



<t t-call="web.external_layout">
External_layout -  використовується на зовнішніх документах, доступних для 
партнерів (логотип + повна інформація про компанію)
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\External_layout.png

<template_id="external_layout">
    <t t-if="not o" t-set="o" t_value="doc"/>

    <t t-if="not company">
        <!-- Multicompany -->
        <t t-if="company_id">
            <t t-set="company" t-value="company_id"/>
        </t>
        <t t-elif="o and 'company_id' in o and o.company_is.sudo()">
            <t t-set="company" t-value="o.company_is.sudo()"/>
         </t>
         <t t-else="else">
            <t t-set="company" t-value="res_company"/>
         </t>
    </t>

    <t t-if="company.external_report_layout_id" t-call="{{ccmpany.externel_report_layout_id.sudo().key}}"><t t-out="0"/></t>
    <t t-else="else" t-call="web.external_layout_standard"><t t-out="0"/></t>
 </template>


<t t-call="web.basic_layout">
Basic_layuot - використовується як каркас для документів
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Basic_layuot.png
 <template id="basic_layout">
    <t t-call="web.html_container">
        <t t-if="not o" t-set="o" t-value="doc"/>
        <div class="article" t-att-data-oe-model="o and o._name" t-att-data-oe-id="o and 0.id" t-att-data-oe-lang="o and o.env.context.get('lang')">
            <t t-out="0"/>
         </div>
    </t>
 </template>

3) Наслідування шаблонів

Успадкування шаблонів дозволяє створити базовий шаблон «скелет», який містить усі загальні елементи вашого звіту та визначає блоки , які дочірні шаблони можуть змінити або доповнити.

<template id="examlpe_template_new" name="Example tenplate" inherit_id="module_name.examlpe_template">

<xpath expr="." position="inside">

## YOUR CODE HERE
</xpath>

</template>


Успадкування в є простим. У шаблоні макета ви можете розміщувати блоки практично скрізь. Дані за межами блоку в дочірньому шаблоні виконуються перед відображенням шаблону макета, тому ви можете використовувати його для поширення даних на весь ланцюжок успадкування. Якщо блок знаходиться в недопустимому положенні, ви отримаєте синтаксичну помилку.



4) Розширення шаблонів

Розширення шаблонів дозволяє змінити існуючий шаблон, доповнити його або забрати лишню інформацію.

<template id="examlpe_template" name="Example tenplate" inherit_id="module_name.examlpe_template">

<xpath expr="." position="inside">

## YOUR CODE HERE
</xpath>

</template>

Головна різниця між наслідуванням і розширенням полягає в тому що при наслідуванні ми створюємо новий шаблон а при розширенні новий шаблон не створюється, а змінюється існуючий 

5) Приклади використання в Odoo


7. Звіти
1) Шаблон звіту

Звіти написані на HTML/QWeb, як і перегляди веб-сайтів у Odoo. Саму візуалізацію PDF виконує wkhtmltopdf .
Звіти оголошуються за допомогою дії звіту та шаблону звіту .Також можна вказати формат паперу для звіту
Шаблони звітів завжди надаватимуть такі змінні:
time
посилання на time стандартну бібліотеку Python
user
Res.user запис для користувача, який друкує звіт
res_company
рекорд для поточної user компанії
website
поточний об’єкт веб-сайту, якщо є (цей елемент може бути присутнім, але None)
web_base_url
базовий URL для веб-сервера
context_timestamp
функція, яка приймає datetime.datetime UTC 1 і перетворює його на часовий пояс користувача, який друкує звіт

<template id="report_invoice">
<t t-call="web.html_container">
<t t-foreach="docs" t-as="o">
<t t-call="web.external_layout">
<div class="page">
<h2>Report title</h2>
<p>This object's name is <span t-field="o.name"/></p>
<div>
<t>
</t>
</t>
</template>

Виклик external_layout додасть верхній і нижній колонтитул за замовчуванням у ваш звіт. Тілом PDF буде вміст всередині файлу . Ім'я шаблону має бути вказаним у декларації звіту; наприклад для наведеного вище звіту. Оскільки це шаблон QWeb, ви можете отримати доступ до всіх полів об’єктів, отриманих шаблоном.<div class="page">id account.report_invoice docs
За замовчуванням контекст візуалізації також надає такі елементи:
docs
записи для поточного звіту
doc_ids
список ідентифікаторів для docs записів
doc_model
модель для docs записів
Якщо ви бажаєте отримати доступ до інших записів/моделей у шаблоні, вам знадобиться спеціальний звіт , однак у цьому випадку вам доведеться надати наведені вище елементи, якщо вони вам потрібні.

Якщо ви хочете перекласти звіти (наприклад, на мову партнера), вам потрібно визначити два шаблони:
●	Основний шаблон звіту
●	Документ для перекладу
Потім ви можете викликати перекладний документ із головного шаблону з атрибутом t-lang, встановленим на код мови (наприклад, frабо en_US) або в поле запису. Вам також потрібно буде повторно переглянути пов’язані записи з належним контекстом, якщо ви використовуєте поля, які можна перекладати (наприклад, назви країн, умови продажу тощо).
Наприклад, розглянемо звіт про замовлення з модуля Продаж:
<!-- Main template -->
<template id="report_saleorder">
   <t t-call="web.html_container">
       <t t-foreach="docs" t-as="doc">
           <t t-call="sale.report_saleorder_document" t-lang="doc.partner_id.lang"/>
       </t>
   </t>
</template>

<!-- Translatable template -->
<template id="report_saleorder_document">
   <!-- Re-browse of the record with the partner lang -->
   <t t-set="doc" t-value="doc.with_context(lang=doc.partner_id.lang)" />
   <t t-call="web.external_layout">
       <div class="page">
           <div class="oe_structure"/>
           <div class="row">
               <div class="col-6">
                   <strong t-if="doc.partner_shipping_id == doc.partner_invoice_id">Invoice and shipping address:</strong>
                   <strong t-if="doc.partner_shipping_id != doc.partner_invoice_id">Invoice address:</strong>
                   <div t-field="doc.partner_invoice_id" t-options="{&quot;no_marker&quot;: True}"/>
               <...>
           <div class="oe_structure"/>
       </div>
   </t>
</template>
Основний шаблон викликає перекладний шаблон з doc.partner_id.lang як t-lang параметр, тому він відображатиметься мовою партнера. Таким чином, кожне замовлення на продаж буде надруковано мовою відповідного клієнта. Якщо ви хочете перекласти лише тіло документа, але залишити верхній і нижній колонтитули мовою за замовчуванням, ви можете викликати зовнішній макет звіту таким чином:
<t t-call="web.external_layout" t-lang="en_US">
Зверніть увагу, що це працює лише під час виклику зовнішніх шаблонів, ви не зможете перекласти частину документа, встановивши t-lang атрибут на вузлі xml, відмінному від t-call. Якщо ви хочете перекласти частину шаблону, ви можете створити зовнішній шаблон з цим частковим шаблоном і викликати його з основного за допомогою t-lang атрибута.

2) Формат листа

Формати паперу є записами report.paperformat та можуть містити такі атрибути:
name(обов'язковий)
корисно лише як мнемоніка/опис звіту під час пошуку звіту в певному списку
description
невеликий опис вашого формату
format
або попередньо визначений формат (A0–A9, B0–B10, Legal, Letter, Tabloid,…) або custom; А4 за замовчуванням. Ви не можете використовувати нестандартний формат, якщо ви визначаєте розміри сторінки.
dpi
вихідний DPI; 90 за замовчуванням
margin_top, margin_bottom, margin_left,margin_right
розміри поля в мм
page_height,page_width
Розмір сторінки в мм
orientation
Пейзаж або портрет
header_line
boolean для відображення рядка заголовка
header_spacing
відстань між колонками в мм
приклад:
<record id="paperformat_frenchcheck" model="report.paperformat">
   <field name="name">French Bank Check</field>
   <field name="default" eval="True"/>
   <field name="format">custom</field>
   <field name="page_height">80</field>
   <field name="page_width">175</field>
   <field name="orientation">Portrait</field>
   <field name="margin_top">3</field>
   <field name="margin_bottom">3</field>
   <field name="margin_left">3</field>
   <field name="margin_right">3</field>
   <field name="header_line" eval="False"/>
   <field name="header_spacing">3</field>
   <field name="dpi">80</field>
</record>


3) Типи звіту QWeb, HTML


Звіти динамічно генеруються модулем іі доступні безпосередньо через URL-адресу:
Наприклад, ви можете отримати доступ до звіту про замовлення в режимі html, перейшовши за адресою http://<адреса-сервера>/report/html/sale.report_saleorder/38
Або ви можете отримати доступ до версії pdf за адресою http://<адреса-сервера>/report/pdf/sale.report_saleorder/38



4) Кастумні звіти

За замовчуванням система звітності створює значення візуалізації на основі цільової моделі, зазначеної в цьому model полі.
Однак спочатку він шукатиме модель з ім’ям і викличе її , щоб підготувати дані візуалізації для шаблону.report.module.report_name_get_report_values(doc_ids, data)
Це можна використовувати для включення довільних елементів для використання або відображення під час візуалізації шаблону, таких як дані з додаткових моделей:
from odoo import api, models
class ParticularReport(models.AbstractModel):
   _name = 'report.module.report_name'

   def _get_report_values(self, docids, data=None):
       # get the report action back as we will need its data
       report = self.env['ir.actions.report'
]._get_report_from_name('module.report_name')
       # get the records selected for this rendering of the report
       obj = self.env[report.model].browse(docids)
       # return a custom rendering context
       return { 'lines': docids.get_lines() }
5) Корисна інформація

Класи Twitter Bootstrap і FontAwesome можна використовувати в шаблоні звіту
Локальний CSS можна помістити безпосередньо в шаблон
Глобальний CSS можна вставити в основний макет звіту, успадкувавши його шаблон і вставивши свій CSS:

<template id="report_saleorder_style" inherit_id="report.style">

 <xpath expr=".">

   <t>
     .example-css-class {
       background-color: red;
     }
   </t>

 </xpath>

</template>

Якщо ви хочете використовувати користувацькі шрифти, вам потрібно буде додати свій власний шрифт і відповідний less/CSS до web.reports_assets_commonпакету активів. Додавання власних шрифтів до web.assets_common або web.assets_backend не зробить ваш шрифт доступним у звітах QWeb.
приклад:
<template id="report_assets_common_custom_fonts" name="Custom QWeb fonts" inherit_id="web.report_assets_common">

<xpath expr="." position="inside">

<link href="/your_module/static/src/less/fonts.less" rel="stylesheet" type="text/less"/>

</xpath>

</template>

Вам потрібно буде визначити свій @font-face у цьому файлі less, навіть якщо ви використовували в іншому наборі активів (окрім web.reports_assets_common).
приклад:
@font-face {
    font-family: 'MonixBold';
    src: local('MonixBold'), local('MonixBold'), url(/your_module/static/fonts/MonixBold-Regular.otf) format('opentype');
}

.h1-title-big {
    font-family: MonixBold;
    font-size: 60px;
    color: #3399cc;
}

Після того, як ви додасте менше у свій пакет активів, ви можете використовувати класи – у цьому прикладі h1-title-big– у своєму спеціальному звіті QWeb.


6) Приклади використання в Odoo

8. Канбан відображення

1) Kanban структура
Перегляди Kanban — це стандартний вигляд Odoo (наприклад, вигляд форми та списку), але їх структура набагато гнучкіша. Фактично, структура кожної картки є поєднанням елементів форми (включаючи базовий HTML) і QWeb. 
Визначення представлення Канбан схоже на визначення представлення списку та форми, за винятком того, що їх кореневий елемент — <kanban>. У своїй найпростішій формі представлення Канбан виглядає так:

<record id="view_model_name_kanban" model="ir.ui.view">
   <field name="name">model.name.kanban</field>
   <field name="model">model.name</field>
   <field name="arch" type="xml">
<kanban>
   <templates>
       <t t-name="kanban-box">
           <div class="oe_kanban_global_click">
               <field name="name"/>
           </div>
       </t>
   </templates>
</kanban>
   </field>
</record>



Давайте розберемо цей приклад:
●	<templates>: визначає список шаблонів QWeb Templates . Перегляди Kanban повинні визначати принаймні один кореневий шаблон kanban-box, який буде відтворюватися один раз для кожного запису.
●	<t t-name="kanban-box">: <t>є елементом-заповнювачем для директив QWeb. У цьому випадку він використовується для встановлення name шаблону kanban-box
●	<div class="oe_kanban_global_click">: oe_kanban_global_clickдозволяє <div> клацати, щоб відкрити запис.
●	<field name="name"/>: це додасть name поле до подання.
Для того щоб відтворювався kanban view_mode, його теба додати в відповідний ir.actions.act_window
<record id="model_name_action" model="ir.actions.act_window">
   <field name="name">Name</field>
   <field name="res_model">model.name</field>
   <field name="view_mode">tree,form,kanban</field> …
2) Приклади використання в Odoo (Аватарки, меню, екшени та інше)

