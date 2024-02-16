==============================================
<?xml version="1.0"?>
<odoo>
  <data>
    <template id="report_custom_template">
      <t t-call="web.html_container">
        <t t-foreach="docs" t-as="doc">
          <div class="report-header">
            <h1>Report Title</h1>
          </div>
          <table class="report-table">
            <thead>
              <tr>
                <th>Column 1</th>
                <th>Column 2</th>
                <th>Column 3</th>
              </tr>
            </thead>
            <tbody>
              <t t-foreach="doc.report_data" t-as="row">
                <tr>
                  <td><t t-esc="row.column_1"/></td>
                  <td><t t-esc="row.column_2"/></td>
                  <td><t t-esc="row.column_3"/></td>
                </tr>
              </t>
            </tbody>
          </table>
        </t>
      </t>
      <t t-set="style">
        <![CDATA[
        .report-header {
          text-align: center;
          margin-bottom: 20px;
        }
        .report-table {
          width: 100%;
          border-collapse: collapse;
        }
        .report-table th,
        .report-table td {
          padding: 5px;
          border: 1px solid #ddd;
        }
        ]]>
      </t>
      <t t-call="web.external_layout">
        <div class="page">
          <style>
            <t t-raw="style"/>
          </style>
          <div class="page-header">
            <h2>Report Title</h2>
          </div>
          <div class="page-content">
            <t t-foreach="docs" t-as="doc">
              <table class="report-table">
                <thead>
                  <tr>
                    <th>Column 1</th>
                    <th>Column 2</th>
                    <th>Column 3</th>
                  </tr>
                </thead>
                <tbody>
                  <t t-foreach="doc.report_data" t-as="row">
                    <tr>
                      <td><t t-esc="row.column_1"/></td>
                      <td><t t-esc="row.column_2"/></td>
                      <td><t t-esc="row.column_3"/></td>
                    </tr>
                  </t>
                </tbody>
              </table>
            </t>
          </div>
        </div>
      </t>
    </template>
  </data>
</odoo>
В этом примере мы создали отчет с заголовком и таблицей данных. Мы использовали CSS для стилизации заголовка и таблицы. Мы также использовали web.external_layout для добавления общего макета отчета и добавили стиль внутри блока стилей style.

======================================================
link
использовать отдельный файл со стилями в QWeb шаблоне
======================================================


------------------------------------------------------
/* style.css */
.my-class {
  color: blue;
  font-weight: bold;
}
------------------------------------------------------
Подключение файла css и использование css class в QWeb шаблоне:

<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <data>
    <template id="my_template" inherit_id="website.layout">
      <xpath expr="//div[@id='wrap']" position="inside">
        <p class="my-class">This text is styled using my-class from style.css file</p>
      </xpath>
      <xpath expr="//head" position="inside">
        <link rel="stylesheet" href="/my_module/static/src/css/style.css"/>
      </xpath>
    </template>
  </data>
</odoo>
В этом примере мы подключаем файл стилей style.css из папки static/src/css нашего модуля и используем класс my-class для стилизации элемента <p>.



------------------------------------------------------
Сначала  создать файл со стилями и сохранить его в папке с модулем Odoo.
Допустим, файл называется styles.css.

------------------------------------------------------
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <template id="report_custom_template">
    <t t-call="web.html_container">
      <t t-foreach="docs" t-as="o">
        <div class="report-header">
          <h1>Report Title</h1>
        </div>
        <div class="report-body">
          <p>Report Content</p>
        </div>
      </t>
    </t>
    <link rel="stylesheet" type="text/css" href="/module_name/static/src/css/styles.css"/>
  </template>
</odoo>

Здесь в теге link указывается относительный путь к файлу со стилями в папке static модуля.
Если файл находится в подпапке, то нужно указать соответствующий путь.

После этого стили из файла styles.css будут применяться к элементам в шаблоне QWeb.
---------------------------------------------------------------




======================================================
использование <style> и class
определяем class: .header, .details, и .details td.
======================================================
<?xml version="1.0" encoding="UTF-8"?>
<odoo>
  <data>
    <template id="report_invoice_document" inherit_id="report.internal_layout">
      <xpath expr="//div[@class='page']" position="inside">
        <style>
          .header {
            background-color: #ccc;
            text-align: center;
            padding: 10px;
            font-size: 20px;
          }
          .details {
            margin-top: 20px;
          }
          .details th {
            background-color: #eee;
            padding: 5px;
            text-align: left;
          }
          .details td {
            padding: 5px;
            text-align: left;
          }
        </style>
        <div class="header">
          <h1>Invoice Report</h1>
        </div>
        <table class="details">
          <thead>
            <tr>
              <th>Product</th>
              <th>Quantity</th>
              <th>Price</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            <tr t-foreach="docs" t-as="doc">
              <td t-field="doc.product_id.name"/>
              <td t-field="doc.quantity"/>
              <td t-field="doc.price"/>
              <td t-field="doc.total"/>
            </tr>
          </tbody>
        </table>
      </xpath>
    </template>
  </data>
</odoo>
