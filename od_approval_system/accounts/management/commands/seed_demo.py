from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.utils import timezone

from accounts.models import DeanProfile, Department, FacultyProfile, School, StudentProfile, UserRole
from od.models import ODApproval, ODCategory, ODRequest, ODStatus, ODRule

User = get_user_model()

OFFICIAL_SAI_DATA = [
    {
        'school': 'School of Computing and Data Science', 'code': 'SCDS',
        'source_url': 'https://www.saiuniversity.edu.in/schools/school-of-computing-and-data-science',
        'deans': [('Dr. Krishna Kant Singh', 'Dean, School of Computing and Data Science')],
        'faculty': [
            ('Dr. Ashok Chandrasekaran', 'Assistant Professor'),
            ('Prof. Krithi Ramamritham', 'Distinguished Professor of Computer Science'),
            ('Dr. Mariya Celin T A', 'Assistant Professor'),
            ('Dr. Saraswathi Krithivasan', 'Assistant Professor of Computer Science'),
            ('Ujjwal Verma', 'Lecturer'),
            ('Dr. Beaula Charles', 'Senior Lecturer'),
        ],
        'departments': [('Computer Science Engineering', 'CSE'), ('Data Science', 'DS'), ('Computing and Data Science', 'CDS')],
    },
    {
        'school': 'School of Arts and Sciences', 'code': 'SAS',
        'source_url': 'https://www.saiuniversity.edu.in/schools/school-of-arts-and-sciences',
        'deans': [('Dr. Sindhuja Sankaran', 'Dean, School of Arts and Sciences')],
        'faculty': [('Dr. Shailender Swaminathan', 'Visiting Professor, Economics'), ('Dr. Sruti Lall', 'Visiting Faculty'), ('Dr. Aravindraja Chairmandurai', 'Visiting Faculty')],
        'departments': [('Economics', 'ECO'), ('Psychology', 'PSY'), ('Biological Sciences', 'BIO')],
    },
    {
        'school': 'School of Law', 'code': 'SOL',
        'source_url': 'https://www.saiuniversity.edu.in/schools/school-of-law',
        'deans': [('Dr. Shiju MV', 'Dean, School of Law')],
        'faculty': [('Anand Shrivas', 'Assistant Professor of Law'), ('Samudyata Sreenath', 'Senior Lecturer'), ('Vikas Bhuvana Muralidharan', 'Lecturer'), ('Anvesh Baki', 'Assistant Professor'), ('Dr. Jaisy George', 'Senior Assistant Professor'), ('Sarath Mohan', 'Assistant Professor')],
        'departments': [('Law', 'LAW'), ('Regulation and Governance', 'REG')],
    },
    {
        'school': 'School of Artificial Intelligence', 'code': 'SAI',
        'source_url': 'https://www.saiuniversity.edu.in/schools/school-of-artificial-intelligence',
        'deans': [('Dr. Ajith Abraham', 'Vice Chancellor and Dean, School of AI')],
        'faculty': [('Dr. Pankaj K Jain', 'Assistant Professor'), ('Dr. Greetta Pinheiro', 'Assistant Professor'), ('Dr. Arunkumar M', 'Assistant Professor')],
        'departments': [('Artificial Intelligence', 'AI'), ('AI and Cybersecurity', 'AIC')],
    },
    {
        'school': 'School of Media', 'code': 'SOM',
        'source_url': 'https://www.saiuniversity.edu.in/schools/school-of-media',
        'deans': [('Prof. (Dr.) Sanjeev Ratna Singh', 'Dean, School of Media')],
        'faculty': [('Dr. Sridhar Krishnaswami', 'Scholar-in-Residence'), ('Avinash Ramachandran', 'Writer and Journalist'), ('Apsara Reddy', 'Journalist')],
        'departments': [('Media Studies', 'MEDIA'), ('Visual Communication', 'VISCOM'), ('Film and Television', 'FTV')],
    },
    {
        'school': 'School of Technology', 'code': 'SOT',
        'source_url': 'https://www.saiuniversity.edu.in/schools/school-of-technology',
        'deans': [('Dr. Toleti Subba Rao', 'Dean, School of Technology')],
        'faculty': [('Dr. Srinivasa Chakravarthy', 'Professor'), ('Dr. Ralf Feser', 'Faculty')],
        'departments': [('Biotechnology', 'BT'), ('Environmental Engineering', 'ENV')],
    },
    {
        'school': 'School of Business', 'code': 'SOB',
        'source_url': 'https://www.saiuniversity.edu.in/schools/school-of-business',
        'deans': [('Dr. Subrata Dey', 'Dean, School of Business')],
        'faculty': [('Dr. Suchit Ahuja', 'Faculty'), ('Dr. Ralph Palliam', 'Dean-CBE / Faculty Reference')],
        'departments': [('Business Administration', 'BBA'), ('Business Analytics', 'BA')],
    },
    {
        'school': 'School of Allied Health Sciences', 'code': 'SAHS',
        'source_url': 'https://www.saiuniversity.edu.in/schools/school-of-allied-health-sciences',
        'deans': [('Dr. K. Kalimuthu', 'Assistant Dean, School of Allied Health Sciences')],
        'faculty': [('Dr. Anil Annamneedi', 'Assistant Professor'), ('Dr. Manobala. T', 'Assistant Professor')],
        'departments': [('Allied Health Sciences', 'AHS'), ('Physiotherapy', 'PHY'), ('Clinical Embryology', 'EMB')],
    },
]


class Command(BaseCommand):
    help = 'Seed Sai University OD Approval System with demo users, official school references, categories, rules, and a sample request.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding Sai University OD Approval System data...')
        categories = ['sports', 'workshop', 'seminar', 'internship', 'placement', 'cultural event', 'technical event', 'NSS/NCC', 'other']
        for c in categories:
            ODCategory.objects.get_or_create(name=c.title())

        school_by_code = {}
        dept_by_code = {}
        dean_user_by_school = {}

        for item in OFFICIAL_SAI_DATA:
            school, _ = School.objects.update_or_create(
                code=item['code'],
                defaults={'name': item['school'], 'official_dean_name': item['deans'][0][0], 'source_url': item['source_url'], 'is_active': True},
            )
            school_by_code[item['code']] = school
            for dept_name, dept_code in item['departments']:
                dept, _ = Department.objects.update_or_create(
                    code=dept_code,
                    defaults={'name': dept_name, 'school': school, 'is_active': True},
                )
                dept_by_code[dept_code] = dept
            ODRule.objects.get_or_create(school=school, department=None, defaults={'max_days_per_month': 5, 'max_days_per_semester': 20})

            for name, designation in item['deans']:
                email = f"{slugify(name).replace('-', '.')}@official.sai.local"
                user, created = User.objects.get_or_create(email=email, defaults={
                    'username': email,
                    'first_name': name,
                    'role': UserRole.DEAN,
                    'is_active': False,
                })
                if created:
                    user.set_unusable_password()
                    user.save()
                profile, _ = DeanProfile.objects.update_or_create(
                    user=user,
                    defaults={'employee_id': f"DEAN-{item['code']}-{user.pk}", 'school': school, 'designation': designation, 'source_url': item['source_url'], 'is_official_seed': True, 'is_active': False},
                )
                dean_user_by_school[item['code']] = user

            default_dept = school.departments.first()
            for name, designation in item['faculty']:
                email = f"{slugify(name).replace('-', '.')}@official.sai.local"
                user, created = User.objects.get_or_create(email=email, defaults={
                    'username': email,
                    'first_name': name,
                    'role': UserRole.FACULTY,
                    'is_active': False,
                })
                if created:
                    user.set_unusable_password()
                    user.save()
                FacultyProfile.objects.update_or_create(
                    user=user,
                    defaults={'employee_id': f"FAC-{item['code']}-{user.pk}", 'school': school, 'department': default_dept, 'dean': dean_user_by_school.get(item['code']), 'designation': designation, 'source_url': item['source_url'], 'is_official_seed': True, 'is_active': False},
                )

        # Active demo users for testing.
        admin = self._create_user('admin@sai.local', 'Admin@12345', 'System', 'Admin', UserRole.ADMIN, is_staff=True, is_superuser=True)
        demo_dean = self._create_user('dean@sai.local', 'Dean@12345', 'Demo', 'Dean', UserRole.DEAN)
        demo_faculty = self._create_user('faculty@sai.local', 'Faculty@12345', 'Demo', 'Faculty', UserRole.FACULTY)
        demo_student = self._create_user('student@sai.local', 'Student@12345', 'Demo', 'Student', UserRole.STUDENT, mobile='9000000000')

        cds = school_by_code['SCDS']
        cse = dept_by_code['CSE']
        DeanProfile.objects.update_or_create(user=demo_dean, defaults={'employee_id': 'DEMO-DEAN-001', 'school': cds, 'designation': 'Demo Dean', 'is_active': True})
        FacultyProfile.objects.update_or_create(user=demo_faculty, defaults={'employee_id': 'DEMO-FAC-001', 'school': cds, 'department': cse, 'dean': demo_dean, 'designation': 'Demo Faculty/Mentor', 'is_active': True})
        StudentProfile.objects.update_or_create(user=demo_student, defaults={'roll_number': 'CDS/2026/0001', 'school': cds, 'department': cse, 'year': 1, 'section': 'A', 'semester': 1, 'mentor': demo_faculty, 'staff_uploaded_login': True, 'uploaded_by': demo_faculty, 'uploaded_at': timezone.now(), 'is_active': True})

        student_profile = demo_student.student_profile
        od_request, created = ODRequest.objects.get_or_create(
            student=student_profile,
            event_title='Workshop',
            defaults={
                'od_type': 'workshop',
                'reason': 'Participating in a department-approved technical workshop.',
                'from_date': date.today() + timedelta(days=3),
                'to_date': date.today() + timedelta(days=3),
                'place': 'Sai University Campus',
                'organizer_details': 'School of Computing and Data Science',
                'status': ODStatus.PENDING_FACULTY_REVIEW,
            },
        )
        if created:
            ODApproval.objects.create(od_request=od_request, action_by=demo_student, role='Student', status=ODStatus.PENDING_FACULTY_REVIEW, remarks='Demo request submitted.')

        self.stdout.write(self.style.SUCCESS('Seed completed.'))
        self.stdout.write('Demo logins:')
        self.stdout.write('Admin   : admin@sai.local / Admin@12345')
        self.stdout.write('Dean    : dean@sai.local / Dean@12345')
        self.stdout.write('Faculty : faculty@sai.local / Faculty@12345')
        self.stdout.write('Student : student@sai.local / Student@12345')

    def _create_user(self, email, password, first_name, last_name, role, mobile='', is_staff=False, is_superuser=False):
        user, created = User.objects.get_or_create(email=email, defaults={
            'username': email,
            'first_name': first_name,
            'last_name': last_name,
            'role': role,
            'mobile': mobile,
            'is_staff': is_staff,
            'is_superuser': is_superuser,
            'is_active': True,
        })
        if created:
            user.set_password(password)
        else:
            user.role = role
            user.is_active = True
            user.is_staff = is_staff or user.is_staff
            user.is_superuser = is_superuser or user.is_superuser
        user.save()
        return user
