from django.shortcuts import HttpResponse, reverse, redirect, render
from django.utils.safestring import mark_safe
from django.db.models import Q
from django.http import QueryDict
from django.db.models.fields.related import ForeignKey, ManyToManyField
from django import forms


# 显示choices字段
def get_display_choices(field, head=None):
    # inner函数才是真正要执行的函数
    def inner(self, header=False, row=None, request=None):
        if header:
            return head
        fun_name = "get_%s_display" % field
        return getattr(row, fun_name)()

    # inner 不用加括号，括号是在执行get_display_choices函数的地方加括号运行
    return inner


class ModelConfigMapping(object):

    def __init__(self, model, config, prev):
        self.model = model
        self.config = config
        self.prev = prev


# 返回字段所对应的value
class Row(object):
    def __init__(self, data, option, query_dict):
        self.data_list = data
        self.option = option
        self.query_dict = query_dict

    def __iter__(self):
        total_params_dict = self.query_dict.copy()
        total_params_dict._mutable = True
        total_valuelist = total_params_dict.getlist(self.option.field)
        yield '<div class="whole">'
        if total_valuelist:
            total_params_dict.pop(self.option.field)
            yield '<a href="?{0}">全部</a>'.format(total_params_dict.urlencode())
        else:
            yield '<a href="?{0}" class="active">全部</a>'.format(total_params_dict.urlencode())
        yield '</div>'
        yield '<div class="others">'
        for obj in self.data_list:
            # 用于a标签文本的显示
            text = self.option.get_text(obj)
            value = str(self.option.get_value(obj))
            query_dict = self.query_dict.copy()
            query_dict._mutable = True
            # 在设置之前首先判断要添加的搜索条件是否在query_dict中，若存在则删除，若不存在则建立
            value_list = query_dict.getlist(self.option.field)
            if self.option.is_multi:
                # 该字段是多选的
                if value in value_list:
                    # 该搜索条件的某一个值已经在该搜索条件的列表中，存在则去除
                    value_list.remove(value)
                    query_dict.setlist(self.option.field, value_list)
                    yield '<a href="?{0}" class="active">{1}</a>'.format(query_dict.urlencode(), text)
                else:
                    # 不存在，把自己添加至列表中
                    value_list.append(value)
                    query_dict.setlist(self.option.field, value_list)
                    yield '<a href="?{0}">{1}</a>'.format(query_dict.urlencode(), text)

            else:
                # 该字段是单选的
                if value in value_list:
                    # 要设置的搜索条件已经在URL参数中，则把该搜索条件从参数中去除。说明当前是被选中的状态，因此需要将当前的a标签设置为active状态
                    query_dict.pop(self.option.field)
                    yield '<a href="?{0}" class="active">{1}</a>'.format(query_dict.urlencode(), text)
                else:
                    query_dict[self.option.field] = value
                    yield '<a href="?{0}">{1}</a>'.format(query_dict.urlencode(), text)
        yield '</div>'


class Option(object):
    def __init__(self, field, is_choice=False, text_fun=None, value_fun=None, is_multi=False):
        self.field = field
        self.is_choice = is_choice
        self.text_fun = text_fun
        self.value_fun = value_fun
        self.is_multi = is_multi

    def get_queryset(self, field_obj, model_class, query_dict):
        if isinstance(field_obj, ForeignKey) or isinstance(field_obj, ManyToManyField):
            row_obj = Row(data=field_obj.rel.model.objects.all(), option=self, query_dict=query_dict)
        else:
            if self.is_choice:
                row_obj = Row(field_obj.choices, option=self, query_dict=query_dict)
            else:
                row_obj = Row(model_class.objects.all(), option=self, query_dict=query_dict)
        yield row_obj

    # 获取每个对象的文本
    def get_text(self, item):
        if self.text_fun:
            return self.text_fun(item)
        # return str(item)
        else:
            if self.is_choice:
                return item[1]
            else:
                return str(item)

    # 获取每一个对象的value
    def get_value(self, item):
        if self.value_fun:
            return self.value_fun(item)
        else:
            if self.is_choice:
                return item[0]
            else:
                return item.pk


class ModelAdmin(object):
    # 要显示的字段
    list_display = ["__str__"]
    # 要排序的规则
    order_by = []
    # 批量操作
    action_list = []
    # 模糊搜索
    search_condition = []
    # 组合搜索
    combinatorial_list = []
    #
    model_form_class = None

    def __init__(self, model_cls, site, prev):
        # 要注册的类
        self.model = model_cls
        # 前缀
        self.prev = prev
        # 实例 site
        self.site = site
        self.back_key = "filter"

    #  显示字段的接口
    def get_list_display(self):
        new_display = []
        new_display.extend(self.list_display)
        new_display.append(ModelAdmin.display_edit_or_delete)
        new_display.insert(0, ModelAdmin.display_checkbox)
        return new_display

    # 指定排序规则
    def get_order_by(self):
        return self.order_by

    # 显示checkbox
    def display_checkbox(self, header=False, row=None, request=None):
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
    def display_edit_or_delete(self, header=False, row=None, request=None):
        """
        显示checkbox
        :param header:
        :param row: 指定选中的对象
        :return:
        """
        if header:
            return "操作"
        tpl = """<a href="{0}"><i class="fa fa-edit" aria-hidden="true"></i></a></a> |
        <a href="{1}"><i class="fa fa-trash-o" aria-hidden="true"></i></a>""".format(self.get_edit_url(row, request),
                                                                                     self.get_delete_url(row, request))
        return mark_safe(tpl)

    # 批量删除
    def multi_delete(self, request):
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

    def get_add_btn(self):
        return mark_safe('<a href="%s" class="btn btn-success">添加</a>' % self.get_add_url(self.request))

    # 获取所有的搜索(只的是用哪些字段进行搜索，不是指的是组合搜索)条件
    def get_search_list(self):
        val = []
        val.extend(self.search_condition)
        return val

    def get_search_condition(self, request):
        search_list = self.get_search_list()
        q = request.GET.get("q", "")
        con = Q()
        con.connector = "OR"
        if q:
            for field in search_list:
                con.children.append(("%s__contains" % field, q))
        return con

    # 获取所有的组合搜索字段
    def get_combinatorial_list(self):
        val = []
        val.extend(self.combinatorial_list)
        return val

    # 组合搜索业务逻辑
    def combinatorial(self):
        # 获取当前表所要组合搜索的字段
        combinatorial_list = self.get_combinatorial_list()
        # 循环要组合搜索的字段
        for item in combinatorial_list:
            # item 得到的是每一个option对象
            # 执行每一个option对象的get_queryset方法，得到了封装了该option对应的queryset的Row实例，并将当前请求的 request.GET的值封装到self中
            # print(self.request.GET)
            yield item.get_queryset(field_obj=self.model._meta.get_field(item.field), model_class=self.model,
                                    query_dict=self.request.GET)

    # 对组合搜索的条件
    def get_combinatorial_condition(self):
        conditions = {}
        for option in self.get_combinatorial_list():
            ele = self.request.GET.getlist(option.field)
            if ele:
                conditions["%s__in" % option.field] = ele
        return conditions

    def changelist_view(self, request, *args, **kwargs):
        if request.method == "POST":
            action = request.POST.get("action")
            if action not in self.get_action_dict():
                return HttpResponse("操作不合法")
            # 执行批量操作
            getattr(self, action)(request)
        self.request = request
        self.get_add_btn()
        return render(request, 'stark/changelist.html', {"self": self, })

    def get_modelform_class(self):
        if self.model_form_class:
            return self.model_form_class

        class DefModelForm(forms.ModelForm):
            class Meta:
                model = self.model
                fields = "__all__"

        return DefModelForm

    def add_view(self, request, *args, **kwargs):
        modelForm = self.get_modelform_class()
        form = modelForm()
        if request.method == "POST":
            form = modelForm(data=request.POST)
            if form.is_valid():
                form.save()
                return redirect(self.get_list_url(request))
        return render(request, "stark/add_or_edit.html", {"form": form})

    def delete_view(self, request, pk, *args, **kwargs):
        if request.method == "POST":
            self.model.objects.filter(pk=pk).delete()
            return redirect(self.get_list_url(request))
        return render(request, "stark/delete.html", )

    def change_view(self, request, pk, *args, **kwargs):
        modelForm = self.get_modelform_class()
        obj = self.model.objects.get(pk=pk)
        form = modelForm(instance=obj)
        if request.method == "POST":
            form = modelForm(data=request.POST, instance=obj)
            if form.is_valid():
                form.save()
                return redirect(self.get_list_url(request))
        return render(request, "stark/add_or_edit.html", {"form": form})

    # 扩展url,为用户添加自定义URL预留接口
    def extra_url(self):
        pass

    @property
    def changelist_url_name(self):
        # 如果有前缀
        if self.prev:
            name = "%s_%s_%s_changelist"%(self.model._meta.app_label, self.model._meta.model_name,self.prev)
        else:
            name = "%s_%s_changelist"%(self.model._meta.app_label, self.model._meta.model_name)
        return name

    @property
    def add_url_name(self):
        # 如果有前缀
        if self.prev:
            name = "%s_%s_%s_add" % (self.model._meta.app_label, self.model._meta.model_name, self.prev)
        else:
            name = "%s_%s_add" % (self.model._meta.app_label, self.model._meta.model_name)
        # data = "stark:%s"%name
        # print(reverse(data))
        return name

    @property
    def edit_url_name(self):
        # 如果有前缀
        if self.prev:
            name = "%s_%s_%s_change" % (self.model._meta.app_label, self.model._meta.model_name, self.prev)
        else:
            name = "%s_%s_change" % (self.model._meta.app_label, self.model._meta.model_name)
        return name

    @property
    def delete_url_name(self):
        # 如果有前缀
        if self.prev:
            name = "%s_%s_%s_delete" % (self.model._meta.app_label, self.model._meta.model_name, self.prev)
        else:
            name = "%s_%s_delete" % (self.model._meta.app_label, self.model._meta.model_name)
        return name

    # 为每个表生成URL
    def get_urls(self):
        """
        为每一个URL生成增删改查4个URL
        :return:
        """
        from django.conf.urls import url
        urlpatterns = [
            url(r'^$', self.changelist_view, name=self.changelist_url_name),
            url(r'^add/$', self.add_view, name=self.add_url_name),
            url(r'^(?P<pk>\d+)/delete/$', self.delete_view, name=self.delete_url_name),
            url(r'^(?P<pk>\d+)/change/$', self.change_view, name=self.edit_url_name),
        ]

        # 添加用户自定义的url
        extra_url = self.extra_url()
        if extra_url:
            urlpatterns.append(extra_url)
        # print(urlpatterns)
        return urlpatterns

    @property
    def urls(self):
        """
        只为了执行 get_urls 方法
        :return:
        """
        return self.get_urls()

    # 获取编辑的URL
    def get_edit_url(self, row, request):
        info = "%s:%s" % (self.site.namespace, self.edit_url_name)
        url = reverse(info, args=(row.pk,))
        _filter = request.GET.urlencode()
        if not _filter:
            return url
        new_query_dict = QueryDict(mutable=True)
        new_query_dict[self.back_key] = _filter
        url = "%s?%s" % (url, new_query_dict.urlencode())
        return url

    # 获取删除的URL
    def get_delete_url(self, row, request):
        info = "%s:%s" % (self.site.namespace, self.delete_url_name)
        url = reverse(info, args=(row.pk,))
        _filter = request.GET.urlencode()
        if not _filter:
            return url
        new_query_dict = QueryDict(mutable=True)
        new_query_dict[self.back_key] = _filter
        url = "%s?%s" % (url, new_query_dict.urlencode())
        return url

    # 获取listURL
    def get_list_url(self, request):
        info = "%s:%s" % (self.site.namespace, self.changelist_url_name)
        url = reverse(info)
        origin_condition = request.GET.get(self.back_key)
        if not origin_condition:
            return url
        url = "%s?%s" % (url, origin_condition)
        return url

    # 获取添加的URL
    def get_add_url(self, request):
        info = "%s:%s" % (self.site.namespace,self.add_url_name)
        url = reverse(info, )
        _filter = request.GET.urlencode()
        if not _filter:
            return url
        new_query_dict = QueryDict(mutable=True)
        new_query_dict[self.back_key] = _filter
        url = "%s?%s" % (url, new_query_dict.urlencode())
        return url


class AdminSite(object):
    def __init__(self):
        # 允许对单个model进行多配置类的注册
        self._registry = []
        self.name = 'stark'
        self.namespace = 'stark'

    def register(self, model_cls, model_config=None, prev=None):
        """
        将APP中的表进行注册(添加到实例site中的_registry中)
        :param model_cls: 要注册的表(类)
        :param model_config: 为当前要注册的表指定的样式类
        :return:
        """
        if not model_config:
            model_config = ModelAdmin
        self._registry.append(
            ModelConfigMapping(model_cls, model_config(model_cls, self, prev), prev)
        )

    def get_urls(self):
        """
        为每一个model进行路由分发
        :return:
        """
        from django.conf.urls import url, include
        urlpatterns = []
        for item in self._registry:
            app_label = item.model._meta.app_label
            model_name = item.model._meta.model_name
            if item.prev:
                urlpatterns += [
                    url(r'^%s/%s/%s/' % (app_label, model_name, item.prev), include(item.config.urls, None, None)),
                ]
            else:
                urlpatterns += [
                    url(r'^%s/%s/' % (app_label, model_name), include(item.config.urls, None, None)),
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
