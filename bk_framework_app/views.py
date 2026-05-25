from django.shortcuts import redirect


def home(request):
    return redirect("analytics:dashboard")


def dev_guide(request):
    return redirect("analytics:dashboard")


def contact(request):
    return redirect("analytics:dashboard")
