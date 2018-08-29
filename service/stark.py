from django.shortcuts import HttpResponse


class ModelAdmin(object):
    def __init__(self, model_cls, site):
        # 要注册的类
        self.model = model_cls
        # 实例 site
        self.site = site

    def changelist_view(self, request, *args, **kwargs):
        return HttpResponse("changelist_view")

    def add_view(self, request, *args, **kwargs):
        return HttpResponse("add_view")

    def delete_view(self, request, pk, *args, **kwargs):
        return HttpResponse("delete_view")

    def change_view(self, request, pk, *args, **kwargs):
        return HttpResponse("changelist_view")

    def get_urls(self):
        """
        为每一个URL生成增删改查4个URL
        :return:
        """
        from django.conf.urls import url

        info = self.model._meta.app_label, self.model._meta.model_name

        urlpatterns = [
            url(r'^$', self.changelist_view, name='%s_%s_changelist' % info),
            url(r'^add/$', self.add_view, name='%s_%s_add' % info),
            url(r'^(?P<pk>\d+)/delete/$', self.delete_view, name='%s_%s_delete' % info),
            url(r'^(?P<pk>\d+)/change/$', self.change_view, name='%s_%s_change' % info),
        ]
        return urlpatterns

    @property
    def urls(self):
        """
        只为了执行 get_urls 方法
        :return:
        """
        return self.get_urls()


class AdminSite(object):
    def __init__(self):
        self._registry = {}
        self.name = 'stark'

    def register(self, model_cls, model_config=None):
        """
        将APP中的表进行注册(添加到实例site中的_registry中)
        :param model_cls: 要注册的表(类)
        :param model_config: 为当前要注册的表指定的样式类
        :return:
        """
        if not model_config:
            model_config = ModelAdmin
        self._registry[model_cls] = model_config(model_cls, self)

    def get_urls(self):
        """
        为每一个model进行路由分发
        :return:
        """
        from django.conf.urls import url, include
        urlpatterns = []
        for model, model_admin in self._registry.items():
            urlpatterns += [
                url(r'^%s/%s/' % (model._meta.app_label, model._meta.model_name), include(model_admin.urls)),
            ]
        return urlpatterns

    @property
    def urls(self):
        """
        为以"stark"开头的路由实现路由分发
        :return: 元组
        """
        return self.get_urls(), 'stark', self.name


site = AdminSite()
