add_comment = function(data) {
  console.log('Adding comment ' + data.comment_added);
  if (data.commit_id){
    // Inline comment
    console.log('Inline');
    var _data = '<tr><td></td><td colspan="2"><table style="width:100%"> \
      <tr><td> \
      <a href="/user/' + data.comment_user + '">'
      + data.comment_user + '</a></td> \
      <td class="right">' + data.comment_date + '</td></tr> \
      <tr><td colspan="2" class="pr_comment">'
      + data.comment_added +
      '</td></tr></table></td></tr>';
    var field = $('[data-commit="' + data.commit_id + '"]').parent();
    var id = field.children().children().attr('id').split('_')[0];
    var row = $('#' + id + '_' + (parseInt(data.line) + 1)).parent().parent();
    row.before(_data);
  } else {
    // Generic comment
    console.log('generic');
    var field = $('#request_comment');
    var _data = '<section class="issue_comment"> \
      <header id="comment-' + data.comment_id + '"> \
        <img class="avatar circle" src="' + data.avatar_url + '"/> \
        <a href="/user/' + data.comment_user + '"> \
          ' + data.comment_user + '\
        </a> - <span title="' + data.comment_date + '">seconds ago</span> \
        <a class="headerlink" title="Permalink to this headline" \
          href="#comment-' + data.comment_id + '">¶</a> \
        <aside class="issue_action icon"> \
          <a class="reply" title="Reply to this comment - loose formating"> \
            reply \
          </a> \
        </aside> \
      </header> \
      <div class="comment_body"> \
        <p>' + data.comment_added + '</p> \
      </div> \
    </section>';

    field.html(field.html() + _data);
  }
}

update_comment = function(data) {
  console.log('Updating comment ' + data.comment_id);
  var field = $('#comment-' + data.comment_id);
  field.find('.edit_date').html(
    '<span title="' + data.comment_date + '">Edited by '
    + data.comment_editor + ' seconds ago</span>');
  var sec = field.parent();
  if (sec.find('.comment_body').length) {
    sec.find('.comment_body').html(data.comment_updated);
  } else {
    sec.parent().parent().find('.comment_date').html(
        '<span title="' + data.comment_date + '">Edited by '
        + data.comment_editor + ' seconds ago</span>');
    sec.parent().parent().find('.pr_comment').html(data.comment_updated);
  }
}

process_event = function(data, requestid){
  console.log(data);
  var category = null;
  var originalTitle = document.title;
  if (data.comment_added){
    add_comment(data);
    category = 'comment';
  } else if (data.comment_updated){
    update_comment(data);
    category = 'Comment updated';
  } else {
    console.log('Unknown data');
  }

  if (category && !document.hasFocus()) {
    var int = setInterval(function(){
      var title = document.title;
      document.title = (title === originalTitle) ? category : originalTitle;
    }, 750);

    $(window).focus(function () {
      clearInterval(int);
      document.title = originalTitle;
    });
  }
}
