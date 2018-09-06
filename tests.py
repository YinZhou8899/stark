from django.shortcuts import HttpResponse,reverse,redirect,render
from django.utils.safestring import mark_safe
from django.db.models import Q
from django.http import QueryDict


class ModelAdmin(object):
    # 要显示的字段
    list_display = []
    # 要排序的规则
    order_by = []
    # 批量操作
    action_list = []
    # 模糊搜索
    search_condition = []

    def __init__(self, model_cls, site):
        # 要注册的类
        self.model = model_cls
        # 实例 site
        self.site = site
        self.back_key = "filter"


    # 指定排序规则
    def get_order_by(self):
        return self.order_by

    # 显示checkbox
    def display_checkbox(self,header=False,row=None,request=None):
        """
        显示checkbox
        :param header:
        :param row: 指定选中的对象
        :return:
        """
        if header:
            return "操作"
        return mark_safe("<input type='checkbox' value='{0}' name='checkbox'>".format(row.pk))

    # 显示操作
    def display_edit_or_delete(self,header=False,row=None,request=None):
        """
        显示checkbox
        :param header:
        :param row: 指定选中的对象
        :return:
        """
        if header:
            return "操作"
        tpl = """<a href="{0}"><i class="fa fa-edit" aria-hidden="true"></i></a></a> |
        <a href="{1}"><i class="fa fa-trash-o" aria-hidden="true"></i></a>""".format(self.get_edit_url(row,request),self.get_delete_url(row,request))
        return mark_safe(tpl)

    # 批量删除
    def multi_delete(self,request):
        checkboxs = request.POST.getlist("checkbox")
        self.model.objects.filter(id__in=checkboxs).delete()
    # 一切皆对象
    multi_delete.derection = "批量删除"

    # 获取所有的批量操作
    def get_action_list(self):
        ret = []
        ret.extend(self.action_list)
        return ret

    # 保存所有的action，用于对action合法性校验
    def get_action_dict(self):
        val = {}
        for item in self.get_action_list():
            val[item.__name__] = item
        return val

    # 获取所有的搜索条件
    def get_search_list(self):
        val = []
        val.extend(self.search_condition)
        return val

    def get_search_condition(self,request):
        search_list = self.get_search_list()
        q = request.GET.get("q","")
        con = Q()
        con.connector = "OR"
        if q:
            for field in search_list:
                con.children.append(("%s__contains"%field,q))
        return con

    def changelist_view(self, request, *args, **kwargs):
        if request.method == "POST":
            action = request.POST.get("action")
            if action not in self.get_action_dict():
                return HttpResponse("操作不合法")
            # 执行批量操作
            getattr(self,action)(request)
        self.request = request
        return render(request,'stark/changelist.html',{"self":self,})

    def add_view(self, request, *args, **kwargs):
        return HttpResponse("add_view")

    def delete_view(self, request, pk, *args, **kwargs):
        return HttpResponse("delete_view")

    def change_view(self, request, pk, *args, **kwargs):
        import time
        time.sleep(3)
        url = self.get_list_url(request)
        return redirect(url)

    # 扩展url,为用户添加自定义URL预留接口
    def extra_url(self):
        pass

    # 为每个表生成URL
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

        # 添加用户自定义的url
        extra_url = self.extra_url()
        if extra_url:
            urlpatterns.append(extra_url)
        return urlpatterns

    @property
    def urls(self):
        """
        只为了执行 get_urls 方法
        :return:
        """
        return self.get_urls()

    # 获取编辑的URL
    def get_edit_url(self,row,request):
        info = "%s:%s_%s_change"%(self.site.namespace,self.model._meta.app_label,self.model._meta.model_name)
        url = reverse(info, args=(row.pk,))
        _filter = request.GET.urlencode()
        if not _filter:
            return url
        new_query_dict = QueryDict(mutable=True)
        new_query_dict[self.back_key] = _filter
        url = "%s?%s" % (url, new_query_dict.urlencode())
        return url

    # 获取删除的URL
    def get_delete_url(self,row,request):
        info = "%s:%s_%s_delete" % (self.site.namespace, self.model._meta.app_label, self.model._meta.model_name)
        url = reverse(info, args=(row.pk,))
        _filter = request.GET.urlencode()
        if not _filter:
            return url
        new_query_dict = QueryDict(mutable=True)
        new_query_dict[self.back_key] = _filter
        url = "%s?%s"%(url,new_query_dict.urlencode())
        return url

    # 获取listURL
    def get_list_url(self,request):
        info = "%s:%s_%s_changelist"%(self.site.namespace,self.model._meta.app_label,self.model._meta.model_name)
        url = reverse(info)
        origin_condition = request.GET.get(self.back_key)
        if not origin_condition:
            return url
        url = "%s?%s" % (url,origin_condition)
        return url


class AdminSite(object):
    def __init__(self):
        self._registry = {}
        self.name = 'stark'
        self.namespace = 'stark'

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
