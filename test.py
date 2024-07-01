from pyresparser import ResumeParser
import warnings
warnings.filterwarnings("ignore", category=UserWarning)


data = ResumeParser('uploads/GAUTAM_BHAGAT_CV.pdf').get_extracted_data()
# print(data)
print("Name:", data["name"])
print("Email:", data["email"])
print("Mobile Number:", data["mobile_number"])
print("Skills:", data["skills"])
print("College Name:", data["college_name"])
print("Degree:", data["degree"])
print("Designation:", data["designation"])
print("Company Names:", data["company_names"])
print("No Of Pages:", data["no_of_pages"])
print("Total Experience:", data["total_experience"])


parsed_data = {
            'name': data.get('name', ''),
            'email': data.get('email', ''),
            'mobile_number': data.get('mobile_number', ''),
            'skills': data.get('skills', []),
            'college_name': data.get('college_name', []),
            'degree': data.get('degree', []),
            'designation': data.get('designation', []),
            'company_names': data.get('company_names', []),
            'total_experience': data.get('total_experience', 0),
            'no_of_pages': data.get('no_of_pages', 0)
        }
        
print(parsed_data)
# print("\n\n\n",data)