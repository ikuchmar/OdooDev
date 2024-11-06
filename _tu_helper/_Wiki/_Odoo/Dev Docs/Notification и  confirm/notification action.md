Для создания уведомления (notification) в Odoo вы можете использовать действие ir.actions.client. 
Это действие позволяет отобразить уведомление пользователю с определенным сообщением и дополнительными действиями.

Вот пример создания уведомления с действием:

    from odoo import models, fields, api
    
    class MyModel(models.Model):
    _name = 'my.model'
    
        def show_notification(self):
            action = {
                'type': 'ir.actions.client',
                'tag': 'notification',
                'params': {
                    'title': 'Уведомление',
                    'text': 'Это сообщение уведомления',
                    'sticky': True,
                    'action_id': self.env.ref('my_module.my_action').id,  # Идентификатор действия для выполнения
                }
            }
            return action

# (вариант выдача сообщений пользователю)

        return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _("Error %s: %s",
                                 res, result.get('errortxt')),
                    'sticky': True,
                }
            }

В этом примере метод show_notification создает действие ir.actions.client с тегом 'notification'. Параметры title и text
определяют заголовок и текст уведомления соответственно. Параметр sticky указывает, будет ли уведомление закреплено в
интерфейсе. action_id содержит идентификатор действия, которое будет выполнено при нажатии на уведомление.

Вы также должны создать соответствующее действие в XML-файле вашего модуля:

    <record id="my_action" model="ir.actions.act_window">
    <field name="name">My Action</field>
    <field name="res_model">my.model</field>
    <field name="view_mode">form</field>
    <field name="view_type">form</field>
    <field name="target">current</field>
    </record>

В этом примере создается действие ir.actions.act_window, которое открывает форму модели 'my.model' в текущем окне.

Теперь, когда вызывается метод show_notification, будет отображено уведомление с заданным сообщением, и при нажатии на
уведомление будет выполнено указанное действие.