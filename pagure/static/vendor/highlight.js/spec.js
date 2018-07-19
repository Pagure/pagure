/*
Language: specfile
Description: RPM Specfile
Author: Ryan Lerch <rlerch@redhat.com>
*/

/*
    The built version of highlight.js truncates a bunch of these
    variables. see https://github.com/isagalaev/highlight.js/blob/905119aad47d4bb3d4fbaa14df7598034dccb6a3/tools/utility.js
    for the list of things it replaces
*/
hljs.registerLanguage("specfile", function(e) {
  return {
    aliases: ['spec'],
    c:[
        hljs.HCM,
        hljs.ASM,
        hljs.QSM,
        {
            cN: "type",
            b:  /^(Name|BuildRequires|Version|Release|Epoch|Summary|Group|License|Packager|Vendor|Icon|URL|Distribution|Prefix|Patch[0-9]*|Source[0-9]*|Requires\(?[a-z]*\)?|[a-z]+Req|Obsoletes|Suggests|Provides|Conflicts|Build[a-z]+|[a-z]+Arch|Auto[a-z]+)(:)/,
        },
        {
            cN: "keyword",
            b: /(%)(?:package|prep|build|description|install|clean|changelog|check|pre[a-z]*|post[a-z]*|trigger[a-z]*|files)/,
        },
        {
            cN: "link",
            b: /(%)(if|else|endif)/,
        },
        {
            cN: "link",
            b: /%\{_/,
            e: /}/,
        },
        {
            cN: "symbol",
            b: /%\{\?/,
            e: /}/,
        },
        {
            cN: "link font-weight-bold",
            b: /%\{/,
            e: /}/,
        },
        {
            cN: "link font-weight-bold",
            b: /%/,
            e: /[ \t\n]/
        },
        {
            cN: "symbol font-weight-bold",
            b: /^\* (Mon|Tue|Wed|Thu|Fri|Sat|Sun)/,
            e: /$/,
        },
    ]
};
});
