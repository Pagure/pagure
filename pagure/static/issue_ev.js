clean_entry= function(text, element) {
  var _out = []
  var _data = $.trim(text).split(',');
  var y=0;
  for (var j=0; j<_data.length; j++){
    if ($.trim(_data[j]) == element) {
      continue;
    }
    _out[y] = $.trim(_data[j]);
    y+=1;
  }
  return _out;
}

add_tags = function(data, _issues_url) {
  console.log('adding ' + data.added_tags);
  var field = $('#taglist');
  var $select = $('#tag').selectize();
  var selectize = $select[0].selectize;

  for (i=0; i<data.added_tags.length; i++ ){
    tag = data.added_tags[i]
    var html = '\n<a id="tag-' + tag + '" class="label label-default" href="'
               + _issues_url + '?tags=' + tag + '"> ' + tag + ' </a>';
    field.append(html);
    selectize.createItem(tag);
  }
}

remove_tags = function(data, _issues_url) {
  console.log('removing ' + data.removed_tags);

  var $select = $('#tag').selectize();
  var selectize = $select[0].selectize;

  for (var i=0; i<data.removed_tags.length; i++ ){
    tag = data.removed_tags[i]
    selectize.removeItem(tag);
    $('#tag-' + tag).remove();
  }
}

assigne_issue = function(data, _issues_url) {
  console.log('assigning ' + data.assigned.name);

  var $select = $('#assignee').selectize();
  var selectize = $select[0].selectize;
  selectize.settings.create = true;
  selectize.createItem(data.assigned.name);
  selectize.settings.create = false;

  var field = $('#assignee_plain');
  var _url = '\n<a href="'
        + _issues_url + '?assignee=' + data.assigned.name + '">'
        + data.assigned.name + '</a>';
  field.html(_url);
}

unassigne_issue = function(data) {
  console.log('un-assigning ');

  var $select = $('#assignee').selectize();
  var selectize = $select[0].selectize;
  selectize.setValue(null);

  var field = $('#assignee_plain');
  field.html('unassigned');
}

add_deps = function(data, issue_uid, _issue_url) {
  console.log('adding ' + data.added_dependency);

  var $select = $('#depends').selectize();
  var selectize = $select[0].selectize;

  if (data.issue_uid == issue_uid){
    if (data.type == "children"){
      var field = $('#blockers');
      var field2 = $('#blocks');
    } else {
      var field = $('#dependencies');
      var field2 = $('#depends');
    }
  }
  var dep = data.added_dependency;
  var _data = $.trim(field.html());
  var _url = _issue_url.replace('/-123456789', '/' + dep) + dep + '</a>';
  if (_data && _data != ',') {
    _data += ',';
  }
  _data += _url;
  field.html(_data);

  var _curval = field2.val().split(',');
  var _values = $.unique($.merge(data.added_dependency, _curval));
  var _out = [];

  if (_out && _out != ',') {
    _out += ',';
  }
  field2.val(_out + dep);
}

remove_deps = function(data, issue_uid, _issue_url) {
  console.log('Removing ' + data.removed_dependency);
  if (data.issue_uid == issue_uid){
    if (data.type == "children"){
      var field = $('#dependencies');
      var field2 = $('#depends');
    } else {
      var field = $('#blockers');
      var field2 = $('#blocks');
    }
  }
  var dep = data.removed_dependency;
  // Set links
  var _data = $.trim(field.html()).split(',');
  var _url = _issue_url.replace('/-123456789', '/' + dep) + dep + '</a>';
  field.html(clean_entry(field.html(), _url).join());
  // Set the value in the input field
  field2.val(clean_entry(field2.val(), dep).join());
}

add_comment = function(data) {
  console.log('Adding comment ' + data.comment_added);
  var field = $('#comments');
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
          </span>\
      ' + data.comment_added + '\
        </div> \
      </section> \
      <div class="issue_actions m-t-2"> \
        <aside class="issue_action icon pull-xs-right p-b-1"> \
          <a class="reply btn btn-secondary btn-sm" data-toggle="tooltip" title="Reply to this comment - loose formating"> \
            reply \
          </a> \
          <a class="edit_btn" data-objid="' + data.issue_id
          + '" data-comment="' + data.comment_id
          + '" href="/test/issue/' + data.issue_id + '/comment/' + data.comment_id + '/edit"> \
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
  field.html(field.html() + _data);
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

update_issue = function(data) {
  console.log('Adjusting issue ' + data.fields);
  for (i=0; i<data.fields.length; i++){
    var _f = data.fields[i];
    if (_f == 'status') {
      var field = $('#status').find('span');
      field.html(data.issue.status);
    } else if (_f == 'title'){
      var field = $('#issuetitle');
      field.html(data.issue.title);
    } else if (_f == 'content'){
      var field = $('#comment-0').parent().find('.comment_body');
      field.html('<p>' + data.issue.content + '</p>');
    }
  }
}

private_issue = function(data, _api_issue_url, issue_uid) {
  if (data.comment_id){
    var _url = _api_issue_url.replace('-123456789', issue_uid)
      + '/comment/' + data.comment_id;
    $.get( _url )
      .done(function(data) {
        add_comment({
          comment_added: data.comment,
          comment_id: data.id,
          comment_user: data.user.name,
          comment_date: data.comment_date,
          avatar_url: data.avatar_url,
        });
      })
  } else if (data.fields) {
    var _url = _api_issue_url.replace('-1', issue_uid) + '?comments=0';
    $.get( _url )
      .done(function(ndata) {
        update_issue({
          fields: data.fields,
          issue: {
            status: ndata.status,
            title: ndata.title,
            content: ndata.content,
          }
        });
      })
  }
}

private_issue_update = function(data, _api_issue_url, issue_uid) {
  var _url = _api_issue_url.replace('-1', issue_uid)
    + '/comment/' + data.comment_id;
  $.get( _url )
    .done(function(data) {
      update_comment({
        comment_updated: data.comment,
        comment_id: data.id,
        comment_user: data.user.name,
        comment_editor: data.comment_date,
      });
    })
}

process_event = function(
      data, issue_uid, _issue_url, _issues_url, _api_issue_url)
{
  console.log(data);
  var category = null;
  var originalTitle = document.title;
  if (data.issue == 'private'){
    console.log('private issue');
    private_issue(data, _api_issue_url, issue_uid)
  }
  else if (data.comment_updated == 'private'){
    console.log('private issue updated');
    private_issue_update(data, _api_issue_url, issue_uid)
  }
  else if (data.added_tags){
    add_tags(data, _issues_url);
    category = 'Tag added';
  }
  else if (data.removed_tags){
    remove_tags(data, _issues_url);
    category = 'Tag removed';
  }
  else if (data.assigned){
    assigne_issue(data, _issues_url);
    category = 'Issue assigned';
  }
  else if (data.unassigned){
    unassigne_issue(data);
    category = 'Issue un-assigned';
  }
  else if (data.added_dependency){
    add_deps(data, issue_uid, _issue_url);
    category = 'Dependency added';
  }
  else if (data.removed_dependency){
    remove_deps(data, issue_uid, _issue_url);
    category = 'Dependency removed';
  }
  else if (data.comment_added){
    add_comment(data);
    category = 'Comment added';
  }
  else if (data.comment_updated){
    update_comment(data);
    category = 'Comment updated';
  }
  else if (data.fields){
    update_issue(data);
    category = 'Issue edited';
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
