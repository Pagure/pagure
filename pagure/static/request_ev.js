add_comment = function(data, username) {
  console.log('Adding comment ' + data.comment_added);
  var field = $('#comments');
  var edit_btn = '<a class="btn btn-secondary btn-sm edit_btn" \
        href="/test/pull-request/' + data.request_id + '/comment/' + data.comment_id + '/edit" \
        data-comment="' + data.comment_id + '" \
        data-objid="' + data.request_id + '"> \
        <span class="oi" data-glyph="pencil"></span> \
    </a>';
  var inline = false;
  if (data.commit_id){
    inline = true;
    edit_btn = '';
  }

  if (data.notification){
      var _data = '<div class="card"> \
            <div class="card-header"> \
              <div> \
                <div class="pull-xs-right text-muted"> \
                  <span title="' + data.comment_date + '">\
                    Just now</span></div>\
                </div> \
                <small>' + emojione.toImage(data.comment_added) + '</small>\
            </div> \
          </div>';

  } else if (inline) {
    var _data = '<tr class="inline-pr-comment"><td></td> \
        <td colspan="2"> \
        <div class="card clearfix m-x-1 "> \
        <div class="card-block"> \
        <small><div id="comment-' + data.comment_id + '"> \
        <img class="avatar circle" src="' + data.avatar_url + '"/> \
        <a href="/user/' + data.comment_user + '"> ' + data.comment_user + '</a> commented  \
        <a class="headerlink" title="Permalink to this headline" \
        href="#comment-' + data.comment_id + '"> \
        <span title="' + data.comment_date + '">Just now</span> \
        </a></div></small> \
        <section class="issue_comment"> \
        <div class="comment_body"> \
        ' + emojione.toImage(data.comment_added) + ' \
        </div> \
        </section> \
        <div class="issue_actions m-t-2"> \
        <aside class="btn-group issue_action icon pull-xs-right p-b-1"> \
            <div class="btn-group" role="group" aria-label="Basic example"> \
              <a class="reply btn btn-secondary btn-sm" data-toggle="tooltip" title="Reply to this comment - lose formatting"> \
                <span class="oi" data-glyph="share-boxed"></span> \
              </a>';
        if ( data.comment_user == username) {
          _data += edit_btn +
              '<button class="btn btn-secondary btn-sm" type="submit" name="drop_comment" value="' + data.comment_id + '" \
                  onclick="return confirm(\'Do you really want to remove this comment?\');" \
                  title="Remove comment"> \
                  <span class="oi" data-glyph="trash"></span> \
                </button>';
            }
        _data += '</div> \
        </aside> \
        </div></div></div> \
        </td></tr>';
  } else {
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
        + emojione.toImage(data.comment_added) + '\
        </div> \
      </section> \
      <div class="issue_actions m-t-2"> \
        <div class="issue_action icon pull-xs-right p-b-1"> \
          <div class="btn-group" role="group" aria-label="Basic example"> \
            <a class="reply btn btn-secondary btn-sm" data-toggle="tooltip" title="Reply to this comment - lose formatting"> \
              <span class="oi" data-glyph="share-boxed"></span> \
            </a>';
    if ( data.comment_user == username) {
        _data += edit_btn +
            '<button class="btn btn-secondary btn-sm" type="submit" name="drop_comment" value="' + data.comment_id + '" \
                onclick="return confirm(\'Do you really want to remove this comment?\');" \
                title="Remove comment"> \
                <span class="oi" data-glyph="trash"></span> \
            </button>';
    }
    _data += '</div> \
        </div> \
    </div>';
  }

  if (inline){
    // Inline comment
    console.log('Inline');
    var field = $('[data-commit="' + data.commit_id + '"]').parent();
    var id = field.children().children().attr('id').split('_')[0];
    var row = $('#' + id + '_' + (parseInt(data.line) + 1)).parent().parent();
    row.before(_data);
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

process_event = function(data, requestid, username){
  console.log(data);
  var category = null;
  var originalTitle = document.title;
  if (data.comment_added){
    add_comment(data, username);
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
