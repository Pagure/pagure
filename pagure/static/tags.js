$(document).ready(function() {
  $("[data-bg-color").each(function(ind, obj) {
    $(obj).css('background-color', $(obj).attr('data-bg-color'));
  });
});