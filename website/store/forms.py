# from django import forms
# from .models import IncomingParcel

# class IncomingParcelForm(forms.ModelForm):
#     class Meta:
#         model = IncomingParcel
#         fields = ['address','city','county','postcode','country','details','pla','petg']

#     def save(self, commit=True):
#         obj = super().save(commit=commit)
#         if commit:
#             obj.ensure_material_rows()
#         return obj