class ToolsLinksHelper:
    """
    Implements the business rule that decides which bot will
    be used.
    """

    AVAILABLE_ENVIRONMENT_MAPPING = {
        "http://localhost:8000": "https://t.me/DudaLocalBot?start=",
        "https://ejplatform.pencillabs.com.br": "https://t.me/DudaEjDevBot?start=",
        "https://www.ejplatform.org": "https://t.me/DudaEjBot?start=",
    }

    @staticmethod
    def get_bot_link(host):
        return (
            ToolsLinksHelper.AVAILABLE_ENVIRONMENT_MAPPING.get(host)
            or "https://t.me/DudaLocalBot?start="
        )
