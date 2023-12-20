related
==========================
Строкове. Послідовність назви полів: поле даної моделі, що посилається на іншу, через точку поле в моделі, на яке посилається дане поле

    survey_id = fields.Many2one('survey.survey', 
                                related='job_id.survey_id', 
                                string="Survey", 
                                readonly=True)








