from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Department, FacultyProfile, DeanProfile, School, StudentProfile, UserRole

User = get_user_model()


class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))


class StudentRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    mobile = forms.CharField(max_length=15, widget=forms.TextInput(attrs={'class': 'form-control'}))
    roll_number = forms.CharField(max_length=40, widget=forms.TextInput(attrs={'class': 'form-control'}))
    school = forms.ModelChoiceField(queryset=School.objects.filter(is_active=True), widget=forms.Select(attrs={'class': 'form-select'}))
    department = forms.ModelChoiceField(queryset=Department.objects.filter(is_active=True), widget=forms.Select(attrs={'class': 'form-select'}))
    year = forms.IntegerField(min_value=1, max_value=6, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    section = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control'}))
    semester = forms.IntegerField(min_value=1, max_value=12, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    mentor = forms.ModelChoiceField(queryset=User.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('first_name', 'last_name', 'email', 'mobile', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mentor'].queryset = User.objects.filter(role=UserRole.FACULTY, is_active=True)
        for field in ['password1', 'password2']:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.role = UserRole.STUDENT
        user.mobile = self.cleaned_data['mobile']
        if commit:
            user.save()
            StudentProfile.objects.create(
                user=user,
                roll_number=self.cleaned_data['roll_number'],
                school=self.cleaned_data['school'],
                department=self.cleaned_data['department'],
                year=self.cleaned_data['year'],
                section=self.cleaned_data['section'],
                semester=self.cleaned_data['semester'],
                mentor=self.cleaned_data.get('mentor'),
            )
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'mobile']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
        }


class StaffUserForm(UserCreationForm):
    role = forms.ChoiceField(choices=[(UserRole.FACULTY, 'Faculty'), (UserRole.DEAN, 'Dean'), (UserRole.ADMIN, 'Admin')], widget=forms.Select(attrs={'class': 'form-select'}))
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    mobile = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    employee_id = forms.CharField(max_length=40, widget=forms.TextInput(attrs={'class': 'form-control'}))
    school = forms.ModelChoiceField(queryset=School.objects.filter(is_active=True), widget=forms.Select(attrs={'class': 'form-select'}))
    department = forms.ModelChoiceField(queryset=Department.objects.filter(is_active=True), required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    designation = forms.CharField(max_length=120, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    dean = forms.ModelChoiceField(queryset=User.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('first_name', 'last_name', 'email', 'mobile', 'role', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        self.allowed_role = kwargs.pop('allowed_role', None)
        self.school_scope = kwargs.pop('school_scope', None)
        super().__init__(*args, **kwargs)
        if self.allowed_role:
            self.fields['role'].choices = [(self.allowed_role, dict(UserRole.choices)[self.allowed_role])]
            self.fields['role'].initial = self.allowed_role
        if self.school_scope:
            self.fields['school'].queryset = School.objects.filter(pk=self.school_scope.pk)
            self.fields['department'].queryset = Department.objects.filter(school=self.school_scope, is_active=True)
        self.fields['dean'].queryset = User.objects.filter(role=UserRole.DEAN, is_active=True)
        for field in ['password1', 'password2']:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data['role']
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.role = role
        user.mobile = self.cleaned_data.get('mobile', '')
        if commit:
            user.save()
            school = self.cleaned_data['school']
            employee_id = self.cleaned_data['employee_id']
            designation = self.cleaned_data.get('designation') or dict(UserRole.choices).get(role, role)
            if role == UserRole.DEAN:
                DeanProfile.objects.create(user=user, employee_id=employee_id, school=school, designation=designation)
            elif role == UserRole.FACULTY:
                department = self.cleaned_data.get('department')
                if not department:
                    raise forms.ValidationError('Department is required for faculty.')
                FacultyProfile.objects.create(
                    user=user,
                    employee_id=employee_id,
                    school=school,
                    department=department,
                    dean=self.cleaned_data.get('dean'),
                    designation=designation,
                )
        return user


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ['name', 'code', 'description', 'official_dean_name', 'source_url', 'is_active']
        widgets = {field: forms.TextInput(attrs={'class': 'form-control'}) for field in ['name', 'code', 'official_dean_name', 'source_url']}
        widgets['description'] = forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        widgets['is_active'] = forms.CheckboxInput(attrs={'class': 'form-check-input'})


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['school', 'name', 'code', 'is_active']
        widgets = {
            'school': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TransferFacultyForm(forms.Form):
    school = forms.ModelChoiceField(queryset=School.objects.filter(is_active=True), widget=forms.Select(attrs={'class': 'form-select'}))
    department = forms.ModelChoiceField(queryset=Department.objects.filter(is_active=True), widget=forms.Select(attrs={'class': 'form-select'}))
    dean = forms.ModelChoiceField(queryset=User.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-select'}))

    def __init__(self, *args, **kwargs):
        school_scope = kwargs.pop('school_scope', None)
        super().__init__(*args, **kwargs)
        if school_scope:
            self.fields['school'].queryset = School.objects.filter(pk=school_scope.pk)
            self.fields['department'].queryset = Department.objects.filter(school=school_scope, is_active=True)
            self.fields['dean'].queryset = User.objects.filter(role=UserRole.DEAN, dean_profile__school=school_scope, is_active=True)
        else:
            self.fields['dean'].queryset = User.objects.filter(role=UserRole.DEAN, is_active=True)


class TransferDeanForm(forms.Form):
    school = forms.ModelChoiceField(queryset=School.objects.filter(is_active=True), widget=forms.Select(attrs={'class': 'form-select'}))


class StudentCredentialUploadForm(forms.Form):
    file = forms.FileField(
        label='Student credential file',
        help_text='Upload CSV or XLSX. Required columns: email, roll_number, password. Add school_code/department_code for admin uploads and department_code for dean uploads.',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.csv,.xlsx'})
    )

    def clean_file(self):
        upload = self.cleaned_data['file']
        name = upload.name.lower()
        if not (name.endswith('.csv') or name.endswith('.xlsx')):
            raise forms.ValidationError('Only CSV and Excel .xlsx files are allowed.')
        if upload.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Upload size must be 5 MB or less.')
        return upload


class SignatureUploadForm(forms.Form):
    signature_image = forms.FileField(
        required=False,
        label='Digital signature image',
        help_text='Upload PNG, JPG, or JPEG. This signature appears on approved OD letters.',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.png,.jpg,.jpeg'})
    )

    def clean_signature_image(self):
        upload = self.cleaned_data.get('signature_image')
        if not upload:
            return upload
        name = upload.name.lower()
        if not name.endswith(('.png', '.jpg', '.jpeg')):
            raise forms.ValidationError('Only PNG, JPG, and JPEG signatures are allowed.')
        if upload.size > 2 * 1024 * 1024:
            raise forms.ValidationError('Signature image must be 2 MB or less.')
        return upload


class TransferStudentForm(forms.Form):
    school = forms.ModelChoiceField(queryset=School.objects.filter(is_active=True), widget=forms.Select(attrs={'class': 'form-select'}))
    department = forms.ModelChoiceField(queryset=Department.objects.filter(is_active=True), widget=forms.Select(attrs={'class': 'form-select'}))
    mentor = forms.ModelChoiceField(queryset=User.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    year = forms.IntegerField(min_value=1, max_value=6, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    section = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control'}))
    semester = forms.IntegerField(min_value=1, max_value=12, widget=forms.NumberInput(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        school_scope = kwargs.pop('school_scope', None)
        super().__init__(*args, **kwargs)
        if school_scope:
            self.fields['school'].queryset = School.objects.filter(pk=school_scope.pk)
            self.fields['department'].queryset = Department.objects.filter(school=school_scope, is_active=True)
            self.fields['mentor'].queryset = User.objects.filter(role=UserRole.FACULTY, faculty_profile__school=school_scope, faculty_profile__is_active=True, is_active=True)
        else:
            self.fields['mentor'].queryset = User.objects.filter(role=UserRole.FACULTY, faculty_profile__is_active=True, is_active=True)
