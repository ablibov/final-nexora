from django import forms
from django.utils.text import slugify

from .models import News, Tag


class PostForm(forms.ModelForm):
    tag_names = forms.CharField(
        required=False,
        max_length=250,
        label='Теги',
        help_text='До 8 тегов через запятую',
        widget=forms.TextInput(attrs={'placeholder': 'Apple, iOS, смартфоны'}),
    )

    class Meta:
        model = News
        fields = ('name', 'description', 'content', 'category', 'topic', 'image', 'source_url', 'status')
        labels = {
            'name': 'Заголовок', 'description': 'Краткое описание',
            'content': 'Текст публикации', 'category': 'Раздел', 'topic': 'Тема',
            'image': 'Обложка', 'source_url': 'Ссылка на источник', 'status': 'Статус',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'content': forms.Textarea(attrs={'rows': 14}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['tag_names'].initial = ', '.join(self.instance.tags.values_list('name', flat=True))

    def clean_tag_names(self):
        raw = self.cleaned_data['tag_names']
        names = list(dict.fromkeys(part.strip().lower() for part in raw.split(',') if part.strip()))
        if len(names) > 8:
            raise forms.ValidationError('Можно указать не больше 8 тегов.')
        if any(len(name) > 40 or not slugify(name, allow_unicode=True) for name in names):
            raise forms.ValidationError('Некорректный тег или слишком длинное название.')
        return names

    def save_tags(self):
        tags = []
        for name in self.cleaned_data['tag_names']:
            tag, _ = Tag.objects.get_or_create(
                slug=slugify(name, allow_unicode=True), defaults={'name': name}
            )
            tags.append(tag)
        self.instance.tags.set(tags)

    def save(self, commit=True):
        post = super().save(commit=commit)
        if commit:
            self.save_tags()
        return post
