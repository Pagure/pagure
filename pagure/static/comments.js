function get_comment_text_from_issue_data(data, commentid) {
    if (commentid) {
        return data['comment'];
    }
    return data['content'];
}

function get_comment_text_from_pr_data(data, commentid) {
    if (commentid) {
        return data['comments'].find(
            element => element['id'] == commentid)['comment'];
    }
    return data['initial_comment'];
}

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

function setup_reply_btns(url, get_comment_text, comment_url_path) {
    $(".reply").unbind();
    $( ".reply" ).click(
        function() {
            var commentid = $( this ).attr('data-comment');

            var comment_url = url;
            if (comment_url_path && commentid) {
                comment_url = comment_url + comment_url_path + commentid;
            }

            $.ajax({
                url: comment_url,
                type: 'GET',
                dataType: 'json',
                success: function(res) {
                    var quote = get_comment_text(res, commentid);
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
    setup_reply_btns(url, get_comment_text_from_issue_data, '/comment/');
}

function setup_pr_reply_btns(url) {
    setup_reply_btns(url, get_comment_text_from_pr_data, '');
}
