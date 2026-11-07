import React from 'react';

// Display isolation only: original message text remains unchanged in state/API.
const tokens = /(\[[0-9٠-٩]+\]|[A-Za-z][A-Za-z0-9_+./:-]*(?:[ \t]+[A-Za-z][A-Za-z0-9_+./:-]*)*|[0-9٠-٩]+(?:[./٫][0-9٠-٩]+)*(?:[%٪])?)/g;
export function RichText({text,inline=false}:{text:string;inline?:boolean}){
 const arabic=/[\u0600-\u06ff]/.test(text);
 const Tag=inline?'span':'div';
 return <Tag className="message-text" dir={arabic?'rtl':'ltr'} lang={arabic?'ar':'en'}>{text.split(tokens).map((part,index)=>
  /^(?:\[[0-9٠-٩]+\]|[A-Za-z0-9٠-٩])/.test(part)?<bdi dir="ltr" key={index}>{part}</bdi>:<React.Fragment key={index}>{part}</React.Fragment>
 )}</Tag>;
}
