add_comment = function(data) {
  console.log('Adding comment ' + data.comment_added);
  var field = $('#comments');
  var edit_btn = '<a class="reply btn btn-secondary btn-sm" \
    data-toggle="tooltip" title="Reply to this comment - loose formating"> \
    reply </a>';
  var inline = false;
  if (data.commit_id){
    inline = true;
    edit_btn = '';
  }

  var _data = '<div class="card clearfix"> \
    <div id="comment-' + data.comment_id + '" class="card-header"> \
    <img class="avatar circle" src="' + data.avatar_url + '"/> \
    <a href="/user/' + data.comment_user + '"> ' + data.comment_user + '\
      </a> \
      <a class="headerlink pull-xs-right" title="Permalink to this headline" \
        href="#comment-' + data.comment_id + '"> \
        <span title="">seconds ago</span> \
       </a>\
    </div>\
    <div class="card-block">\
      <section class="issue_comment"> \
        <div class="comment_body"> \
          <span class="edit_date" title=""> \
          </span>'
        + data.comment_added + '\
        </div> \
      </section> \
      <div class="issue_actions m-t-2"> \
        <aside class="issue_action icon pull-xs-right p-b-1">'
          + edit_btn
          + '<a class="edit_btn" data-objid="' + data.request_id
          + '" data-comment="' + data.comment_id
          + '" href="/test/pull-request/' + data.request_id + '/comment/' + data.comment_id + '/edit"> \
            <span class="icon icon-edit blue"></span> \
          </a> \
          <button class="btn btn-danger btn-sm" \
            title="Remove comment" \
            name="drop_comment" value="' + data.comment_id + '" type="submit"  \
            onclick="return confirm(\'Do you really want to remove this comment?\');" \
            ><span class="oi" data-glyph="trash"></span> \
          </button> \
        </aside> \
      </div> \
    </div> \
    </div>';

  if (inline){
    // Inline comment
    console.log('Inline');
    var _row = '<tr><td></td><td colspan="2"><table style="width:100%"> \
      <tr><td>' + _data + '</td></tr></table></td></tr>';
    var field = $('[data-commit="' + data.commit_id + '"]').parent();
    var id = field.children().children().attr('id').split('_')[0];
    var row = $('#' + id + '_' + (parseInt(data.line) + 1)).parent().parent();
    row.before(_row);
  } else {
    // Generic comment
    console.log('generic');
    var field = $('#request_comment');
    field.html(field.html() + _data);
  }
}

update_comment = function(data) {
  console.log('Updating comment ' + data.comment_id);
  var field = $('#comment-' + data.comment_id).parent();
  var edited = field.find('.text-muted');
  if (edited.length == 0) {
    $(field.find('aside')).before(
        '<small class="text-muted">Edited a just now by '
        + data.comment_editor + '</small>');
  } else {
    edited.html('Edited a just now by ' + data.comment_editor)
  }
  field.find('.comment_body').html(data.comment_updated);
  field.find('.issue_actions').show();
  field.find('.issue_comment').show();
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
