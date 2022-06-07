from django.shortcuts import render
# Create your views here.


def main(request):
    return render(
        request,
        'main.html'
    )


def search(request, user_id):
    return render(
        request,
        'result.html'
    )