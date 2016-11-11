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

  var $select = $('#tag').selectize();
  var selectize = $select[0].selectize;

  var field = $('#taglist');
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
  $('#assignee').val(data.assigned.name);

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

  var dep = data.added_dependency;
  if (data.issue_uid == issue_uid){
    if (data.type == "children"){
      var $select = $('#blocks').selectize();
      var field = $('#blocklist');
      var _id = 'block';
    } else {
      var $select = $('#depends').selectize();
      var field = $('#dependlist');
      var _id = 'depend';
    }
  }

  var selectize = $select[0].selectize;
  selectize.settings.create = true;
  selectize.items.push(String(dep));
  selectize.createItem(String(dep));
  selectize.settings.create = false;

  var input_field = $('#' + _id + 's');
  input_field.val(selectize.items.join(','));

  var html = '\n<a id="' + _id + '-' + dep + '" class="label label-default" href="'
               + _issue_url.replace('/-123456789', '/' + dep) + '">#' + dep + '</a>';

  field.append(html);
}

remove_deps = function(data, issue_uid, _issue_url) {
  console.log('Removing ' + data.removed_dependency);
  if (data.issue_uid == issue_uid){
    if (data.type == "children"){
      var $select = $('#depends').selectize();
      var _id = 'depend';
    } else {
      var $select = $('#blocks').selectize();
      var _id = 'block';
    }
  }

  var selectize = $select[0].selectize;

  var dep = data.removed_dependency;
  $('#' + _id + '-' + dep).remove();
  selectize.removeItem(dep);
}

add_comment = function(data, username) {
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
      ' + emojione.toImage(data.comment_added) + '\
        </div> \
      </section> \
      <div class="issue_actions m-t-2"> \
        <aside class="issue_action icon pull-xs-right p-b-1"> \
        <div class="btn-group" aria-label="Basic example" role="group"> \
        <a class="reply btn btn-secondary btn-sm" title="" data-toggle="tooltip" data-original-title="Reply to this comment - loose formating"> \
            <span class="oi" data-glyph="share-boxed"></span> \
        </a>';
    if ( data.comment_user == username) {
          _data += '<a class="btn btn-secondary btn-sm" data-objid="' + data.issue_id
          + '" data-comment="' + data.comment_id
          + '" href="/' + data.project + '/issue/' + data.issue_id + '/comment/' + data.comment_id + '/edit"> \
            <span class="oi" data-glyph="pencil"></span> \
          </a> \
          <button class="btn btn-secondary btn-sm" \
            title="Remove comment" \
            name="drop_comment" value="' + data.comment_id + '" type="submit"  \
            onclick="return confirm(\'Do you really want to remove this comment?\');" \
            ><span class="oi" data-glyph="trash"></span> \
          </button>';
    }
    _data += '</aside> \
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

update_custom_fields = function(data) {
  console.log('Adjusting custom fields ' + data.custom_fields);
  for (i=0; i<data.custom_fields.length; i++){
    var _f = data.custom_fields[i];
    var field = $('#' +  _f);
    var _val = null;
    for (j=0; j<data.issue.custom_fields.length; j++) {
      if (data.issue.custom_fields[j].name == _f){
        if (data.issue.custom_fields[j].key_type == 'boolean'){
          _val = data.issue.custom_fields[j].value == 'on';
        } else {
          _val = data.issue.custom_fields[j].value;
        }
        break;
      }
    }
    if (_val == null) {
      console.log('No corresponding custom field/value found');
      return
    }
    if (_val == true || _val == false) {
      field[0].checked = _val;
    } else {
      field.val(_val);
    }

    var field = $('#' +  _f + '_plain');
    field.html(_val);
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
      data, issue_uid, _issue_url, _issues_url, _api_issue_url, username)
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
    add_comment(data, username);
    category = 'Comment added';
  }
  else if (data.comment_updated){
    update_comment(data);
    category = 'Comment updated';
  }
  else if (data.custom_fields){
    update_custom_fields(data);
    category = 'Custom fields edited';
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
