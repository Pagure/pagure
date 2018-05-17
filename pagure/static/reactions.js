(function () {
    function send_reaction(commentid, reaction, emoji) {
        var _url = location.href + '/comment/' + commentid + '/react';
        var csrf_token = $("#csrf_token").val();
        $.ajax({
            url: _url + '?js=1',
            type: 'POST',
            data: {
                'reaction': reaction,
                'csrf_token': csrf_token,
            },
            success: function () {
                var reactions = $(".issue_reactions[data-comment-id=" + commentid + "]>.btn-group");
                var selected = reactions.find("span[class=" + emoji + "]");
                if (selected.length > 0) {
                    var counter = selected.next();
                    counter.text(parseInt(counter.text(), 10) + 1);
                } else {
                    reactions.append(
                        '<button class="btn btn-outline-secondary btn-sm" type="button">' +
                            '    <span class="' + emoji + '"></span>' +
                            '    <span class="count">' + 1 + '</span>' +
                            '</button>');
                }
            },
        });
    }

    $(document).ready(function () {
        $(".reaction-picker button").click(function () {
            var commentid = $(this).parents('.reaction-picker').data('comment-id');
            var reaction = $(this).attr('title');
            var emoji = $(this).find('span').attr('class');
            send_reaction(commentid, reaction, emoji);
        });
    });
})();
