from django.contrib import admin

from .models import CustomUser, Customer, Employee, OngoingSync, Toggles


# class UserCreateForm(UserCreationForm):
#     """ Custom User Form """
#     class Meta:
#         """ Meta """
#         model = AbstractBaseUser
#         fields = ('username', 'first_name', 'last_name', )

# class UserAdmin(BaseUserAdmin):
#     """ Custom User Admin """
#     add_form = UserCreateForm
#     prepopulated_fields = {'username': ('first_name', 'last_name', )}

#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('first_name', 'last_name', 'email', 'username', 'password1', 'password2', ),
#         }),
#     )

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['email']
    
    def __str__(self):
        return self.email

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """ Customer Admin """
    list_display = ["user"]

    def get_form(self, request, obj=None, **kwargs):
        if not obj:  # Create form
            kwargs['exclude'] = ('first_name', 'last_name', 'email', 'PIPEDRIVE_PERSON_STRIPE_URL_KEY', 'PIPEDRIVE_DEAL_PROCESS_NOW_SELECTOR')
        return super().get_form(request, obj, **kwargs)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    """ Employee Admin """
    list_display = ["user"]

@admin.register(Toggles)
class TogglesAdmin(admin.ModelAdmin):
    """ Toggles Admin """
    list_display = ["name"]

@admin.register(OngoingSync)
class OngoingSyncAdmin(admin.ModelAdmin):
    """ OngoingSync Admin """""
    list_display = ["type"]

# # Re-register UserAdmin
# admin.site.unregister(AbstractBaseUser)
# admin.site.register(AbstractBaseUser, UserAdmin)
