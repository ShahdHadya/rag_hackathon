import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readChatResponse,unavailable} from '../dist/api-test.mjs';

test('empty proxy response during restart gives a recoverable message',async()=>{
 await assert.rejects(readChatResponse(new Response('',{status:500})),{message:unavailable});
});
test('empty success response is never treated as a valid answer',async()=>{
 await assert.rejects(readChatResponse(new Response('',{status:200})),{message:unavailable});
});
test('HTML proxy errors do not leak JSON parsing exceptions',async()=>{
 await assert.rejects(readChatResponse(new Response('<html>Bad gateway</html>',{status:502})),{message:unavailable});
});
test('truncated JSON is rejected clearly',async()=>{
 await assert.rejects(readChatResponse(new Response('{"answer":',{status:200})),/غير مكتمل/);
});
test('missing fields cannot become a valid answer',async()=>{
 await assert.rejects(readChatResponse(Response.json({answer:'missing citations'})),/غير مكتمل/);
});
test('a valid cited answer preserves nullable metadata',async()=>{
 const body={answer:'SWER401: 1 ساعة [1]',kind:'lookup',citations:[{id:1,title:'courses.pdf',page:2,url:null,caution:null,label:null,csv_row:null,course_code:null}]};
 assert.deepEqual(await readChatResponse(Response.json(body)),body);
});
