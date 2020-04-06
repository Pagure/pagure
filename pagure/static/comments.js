function reply(quote) {
    var text = $.trim($( "#comment" ).val());
    if (text.length > 0) {
        text += "\n\n";
    }

    var lines = quote.split("\n");
    for (var i = 0; i < lines.length ; i++) {
        text += '> ' + $.trim(lines[i]) + "\n";
    }

    $( "#comment" ).val(text + "\n");
    $( "#comment" ).focus();
}

function setup_reply_btns(url, initial_comment_key) {
    $(".reply").unbind();
    $( ".reply" ).click(
        function() {
            var commentid = $( this ).attr('data-comment');

            var comment_url = url;
            if (commentid) {
                comment_url = comment_url + '/comment/' + commentid;
            } else {
                comment_url = comment_url + '?comments=false';
            }

            $.ajax({
                url: comment_url,
                type: 'GET',
                dataType: 'json',
                success: function(res) {
                    var quote = res[commentid ? 'comment' : initial_comment_key];
                    reply(quote)
                },
                error: function() {
                    alert('Failed to retrieve comment text');
                }
            });
        }
    ).click(
        function() {
            $('html, body').animate({
                scrollTop: $("#comment").offset().top
            }, 2000);
        }
    );
};

function setup_issue_reply_btns(url) {
    setup_reply_btns(url, 'content');
}

function setup_pr_reply_btns(url) {
    setup_reply_btns(url, 'initial_comment');
}
