from django.shortcuts import redirect

def redirect_to_login_page(get_response):
    def middleware(request):
        response = get_response(request)
        if request.GET.get('origin'):
            if not request.user.is_authenticated:
                comment_id = request.GET.get('comment_id')
                vote = request.GET.get('vote')
                query_params = '&comment_id={}&vote={}'.format(comment_id, vote)
                path = request.path
                login_url = '/login?next={}{}'.format(path, query_params)
                return redirect(login_url)
            else:
                return response
        else:
            return response
    return middleware
