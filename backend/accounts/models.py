from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


def normalize_email(email):
    return email.strip().lower()


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, username):
        return self.get(email=normalize_email(username))

    def create_user(self, email, password=None, **extra_fields):
        if not email or not email.strip():
            raise ValueError("Укажите email.")
        user = self.model(email=normalize_email(email), **extra_fields)
        user.set_password(password)
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Суперпользователь должен иметь is_staff и is_superuser.")
        if not password:
            raise ValueError("Укажите пароль суперпользователя.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    first_name = None
    last_name = None
    email = models.EmailField("email", max_length=254, unique=True)
    full_name = models.CharField("имя и фамилия", max_length=150)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]
    objects = UserManager()

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"
        constraints = [models.UniqueConstraint(Lower("email"), name="user_email_lower_unique")]

    def clean(self):
        super().clean()
        self.email = normalize_email(self.email)

    def save(self, *args, **kwargs):
        self.email = normalize_email(self.email)
        super().save(*args, **kwargs)

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name

    def __str__(self):
        return self.email
