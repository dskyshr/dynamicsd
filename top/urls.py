from django.urls import path
from .views import TopView

app_name = 'top'

urlpatterns = [
    # TOP
    #path('', TopView.as_view(), name='top'),
    path('', TopView, name='top'),
]
