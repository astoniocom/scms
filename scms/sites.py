class SCMSSite(object):
    def __init__(self):
        self._content_types = {}

    def register_content_type(self, contene_type):
        self._content_types[contene_type.id] = contene_type

    def get_content_type(self, content_type = None):
        if not content_type is None:
            if content_type in self._content_types:
                return self._content_types[content_type]
            else:
                return None
        return self._content_types
site = SCMSSite()