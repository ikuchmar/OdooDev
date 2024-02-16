qWeb Report

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


