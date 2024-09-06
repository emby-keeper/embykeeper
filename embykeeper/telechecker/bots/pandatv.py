from ._templ_a import TemplateACheckin


class PandaTVCheckin(TemplateACheckin):
    name = "PandaTV"
    bot_username = "PandaTV_Emby_Bot"
    bot_checkin_cmd = "/start"
    checked_retries = 6
