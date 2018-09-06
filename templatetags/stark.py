from django.template import Library
from types import FunctionType
from stark.utils.pagination import Pagination

register = Library()


@register.inclusion_tag('stark/content.html')
def content(self):
    # 获取筛选条件----> (OR: ('name__contains', '白'))
    filter_conditions = self.get_search_condition(self.request)

    # 获取组合搜索条件
    def get_rows():
        data = self.combinatorial()
        for item in data:
            for row_obj in item:
               yield row_obj
    # 过滤
    queryset = self.model.objects.filter(filter_conditions).filter(**self.get_combinatorial_condition()).order_by(*self.get_order_by())
    # 获取当前搜索条件，对搜索出的数据进行分页显示
    query_params = self.request.GET.copy()
    # 点击不同的页码需要更改page的值，因此需要设置为True
    query_params._mutable = True

    # 分页初始化
    page = Pagination(current_page=self.request.GET.get("page"),all_count=queryset.count(),base_url=self.request.path_info,query_params=query_params,per_page=3)
    # 对过滤后的数据进行分页
    queryset = queryset[page.start:page.end]
    list_display = self.get_list_display()
    action_list = [{"name":item.__name__,"derection":item.derection} for item in self.get_action_list()]

    def header_list():
        if list_display:
            for name in list_display:
                # 对要显示的是表的字段或者是checkbox进行判断
                if isinstance(name, FunctionType):
                    verbose_name = name(self, header=True)
                else:
                    if name == "__str__":
                        verbose_name = "标题"
                    else:
                        verbose_name = self.model._meta.get_field(name).verbose_name
                yield verbose_name
        else:
            yield self.model._meta.model_name

    def body_list():
        for row in queryset:
            row_list = []
            if not list_display:
                row_list.append(row)
                yield row_list
                continue
            for name in list_display:
                if isinstance(name, FunctionType):
                    val = name(self, row=row,request=self.request)
                else:
                    val = getattr(row, name)
                row_list.append(val)
            yield row_list
    return {'header_list': header_list(), 'body_list': body_list(),"action_list":action_list,"page":page,"rows":get_rows(),"add_btn":self.get_add_btn()}
