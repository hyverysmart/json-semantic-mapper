def show_field(field_name):
    print(field_name)

show_field("studentName")
show_field("studentId")

def countdown(n):
    print(n)

    if n>1:
        countdown(n-1)

countdown(2)