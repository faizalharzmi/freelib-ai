from django import forms


class SearchForm(forms.Form):
    q = forms.CharField(max_length=200, min_length=2, strip=True,
        widget=forms.TextInput(attrs={'placeholder': "Describe the book you're looking for...", 'autocomplete': 'off'}))
    page = forms.IntegerField(min_value=1, max_value=100, required=False, initial=1)
