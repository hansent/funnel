from funnel import RouteList
from funnel.handlers import BaseHandler
from tornado.web import HTTPError



class APIManager(RouteList):
    def _create_handler(self, model):
        handler_name = "%sAPIResource" % model.__name__.split('.')[-1]
        handler = type(handler_name, (APIResource,), {'model':model} )
        return handler

    def add_resource(self, resource, path=None, pattern=None, name=None):
        if not issubclass(resource, APIResource):
            resource = self._create_handler(resource)
        if not path:
            path = "/%s" % resource.model.__name__.lower().split('.')[-1]
        if not pattern:
            pattern = "(?:$|/([0-9]+)?)"
        route_pattern = path + pattern
        self.add_route(route_pattern, resource, name=name)


class APIHandler(BaseHandler):
    pass

class APIResource(APIHandler):
    model = None

    def list_resources(self):
        return self.model.find_all()

    def get_resource(self, resource_id):
        return self.model.get(resource_id)

    def create_resource(self):
        return self.model(**self.json_data).put()

    def update_resource(self, resource_id):
        instance = self.model.get(resource_id)
        if not instance:
            return None
        for k,v in self.json_data.iteritems():
            setattr(instance, k, v)
        return instance.put()

    def delete_resource(self, resource_id):
        instance = self.model.get(resource_id)
        instance.delete()
        return {}

    def get(self, resource_id=None):
        if not resource_id:
            return self.list_resources()
        instance = self.get_resource(resource_id)
        if not instance:
            raise HTTPError(404, "Resource not found")
        return instance

    def post(self, resource_id):
        if not resource_id:
            return self.create_resources()
        instance = self.update_resource(resource_id)
        if not instance:
            raise HTTPError(404, "Resource not found")
        return instance

    def delete(self, resource_id):
        self.delete_resource(resource_id)



