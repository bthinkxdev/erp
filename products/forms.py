from django import forms

from .models import Product, ProductCategory


class ProductCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ("name", "image", "is_active")

    def __init__(self, *args, vendor=None, **kwargs):
        self._vendor = vendor
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self._vendor is not None:
            obj.vendor = self._vendor
        if commit:
            obj.save()
        return obj


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ("name", "category", "description", "image", "price", "mrp", "is_active")
        widgets = {
            "category": forms.Select(
                attrs={
                    "class": (
                        "w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-lg "
                        "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
                    )
                }
            ),
        }

    def __init__(self, *args, vendor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if vendor is not None:
            self.fields["category"].queryset = ProductCategory.objects.filter(
                vendor=vendor, is_active=True
            ).order_by("name")
            self.fields["category"].required = False
            self.fields["category"].empty_label = "No category"
        else:
            self.fields["category"].queryset = ProductCategory.objects.none()
