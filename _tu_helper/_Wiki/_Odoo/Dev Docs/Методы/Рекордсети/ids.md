
self.requisition_id.line_ids.product_id.ids

Властивість ids містить список значеннь id записів, що входять в рекордсет. 
Оскільки поля x2many є рекордсетами, вони теж мають цей атрибут


class AModel(models.Model):
   _name = 'a.model'

   def a_method(self):
       print(self.ids)
       print(self.line_ids.ids)
