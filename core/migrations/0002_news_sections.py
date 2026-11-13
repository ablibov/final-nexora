from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='news',
            name='image',
            field=models.ImageField(blank=True, upload_to='newsphotos/'),
        ),
        migrations.AlterField(
            model_name='news',
            name='name',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='news',
            name='description',
            field=models.TextField(max_length=500),
        ),
        migrations.AddField(
            model_name='news',
            name='content',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='news',
            name='category',
            field=models.CharField(choices=[('news', 'Новости'), ('articles', 'Статьи'), ('reviews', 'Обзоры')], default='news', max_length=20),
        ),
        migrations.AddField(
            model_name='news',
            name='topic',
            field=models.CharField(choices=[('other', 'Другое'), ('iphone-17', 'iPhone 17'), ('iphone-18', 'iPhone 18'), ('iphone-duo', 'iPhone Duo'), ('ios-27', 'iOS 27')], default='other', max_length=20),
        ),
        migrations.AddField(
            model_name='news',
            name='source_url',
            field=models.URLField(blank=True, default=''),
        ),
        migrations.AlterModelOptions(
            name='news',
            options={'ordering': ['-created_at', '-id'], 'verbose_name': 'Публикация', 'verbose_name_plural': 'Публикации'},
        ),
    ]
