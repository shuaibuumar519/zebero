from flask import (
    render_template,
    session,
    redirect,
    request,
)

from referral.models import (
    create_referral_code,
    get_referral_code,
    count_referrals,
)


def referral_page():

    if "user" not in session:
        return redirect("/login")

    user_id = session["user"]["id"]

    code = get_referral_code(user_id)

    if not code:
        code = create_referral_code(user_id)

    referral_link = (
        request.host_url.rstrip("/")
        + "/?ref="
        + code
    )

    total = count_referrals(code)

    return render_template(
        "referral/index.html",
        referral_code=code,
        referral_link=referral_link,
        total_referrals=total,
    )
