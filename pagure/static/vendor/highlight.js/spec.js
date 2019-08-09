/*
Language: rpm-specfile
Description: RPM Specfile
Author: Ryan Lerch <rlerch@redhat.com>
Contributors: Neal Gompa <ngompa13@gmail.com>
*/

/*
    The built version of highlight.js truncates a bunch of these
    variables. see https://github.com/isagalaev/highlight.js/blob/905119aad47d4bb3d4fbaa14df7598034dccb6a3/tools/utility.js
    for the list of things it replaces
*/
hljs.registerLanguage("rpm-specfile", function(e) {
  return {
    aliases: ['rpm', 'spec', 'rpm-spec', 'specfile'],
    c:[
        hljs.HCM,
        hljs.ASM,
        hljs.QSM,
        {
            cN: "type",
            b:  /^(Name|BuildRequires|BuildConflicts|Version|Release|Epoch|Summary|Group|License|Packager|Vendor|Icon|URL|Distribution|Prefix|Patch[0-9]*|Source[0-9]*|Requires\(?[a-z]*\)?|[a-zA-Z]+Req|Obsoletes|Recommends|Suggests|Supplements|Enhances|Provides|Conflicts|RemovePathPostfixes|Build[a-zA-Z]+|[a-zA-Z]+Arch|Auto[a-zA-Z]+)(:)/,
        },
        {
            cN: "keyword",
            b: /(%)(?:package|prep|generate_buildrequires|sourcelist|patchlist|build|description|install|verifyscript|clean|changelog|check|pre[a-z]*|post[a-z]*|trigger[a-z]*|files)/,
        },
        {
            cN: "link",
            b: /(%)(if|ifarch|ifnarch|ifos|ifnos|elif|elifarch|elifos|else|endif)/,
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
