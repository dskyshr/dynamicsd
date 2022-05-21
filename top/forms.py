from django import forms
#from .models import Conditions

"""
class ConditionsForm(forms.ModelForm):

    class Meta:
        model = Conditions
        fields = (
            'participants',
            'initial_dist',
        #    'memo',
        )
        widgets = {
            'participants':forms.TextInput(),
            'initial_dist':forms.Select(),
            #'memo':forms.TextInput(
            #    attrs={'placeholder': '8519'}
            #),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['house'].widget.render_value = True

        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
"""

# 初期選択肢分布
INIT_DIST_CHOICES = (
    (1, "①線形"),
    (2, "②凸型"),
    (3, "③凹型"),
)
# メカニズム
MECHANISM = (
    (1, "複合優先順序メカニズム"),
    (2, "確率的ボストンメカニズム"),
)
# CSVファイルの出力
CSV_WRITE_MODE = (
    (1, "New"),
    (2, "Append"),
)

class ConditionsForm(forms.Form):
    # 市場参加者数
    participants = forms.IntegerField(
        label='Number of Participants',
        widget=forms.TextInput(),
        initial=8519,
    )
    initial_dist = forms.ChoiceField(
        label='Initial Distribution of Options',
        choices=INIT_DIST_CHOICES,
    )
    term = forms.IntegerField(
        label='Number of Matching Term',
        widget=forms.TextInput(),
        initial=50,
    )
    mechanism = forms.ChoiceField(
        label='Mechanism',
        choices=MECHANISM,
    )
    csv = forms.BooleanField(
        label='Print as CSV file',
        required=False,
        disabled=False,
        initial=1,
    )
    csv_write_mode = forms.ChoiceField(
        label='CSV Writing Mode',
        widget=forms.widgets.RadioSelect,
        choices=CSV_WRITE_MODE,
    )
