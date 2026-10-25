type ty = Int | Bool | Str | Unit
type span = { lo:int; hi:int; line:int; column:int }
type token_kind = Id of string | Number of int64 | Text of string | Hole of string option | Sym of string | Eof
type token = { kind:token_kind; at:span }
type expr =
  | EInt of int64*span | EBool of bool*span | EStr of string*span
  | EName of string*span | EHole of string option*span
  | ECall of string*expr list*span | EBin of string*expr*expr*span | EIf of expr*expr*expr*span
type stmt = SLet of string*ty option*expr*span | SReturn of expr*span | SBlock of stmt list*span | SExpr of expr*span
type func = { fname:string; params:(string*ty*span) list; result:ty; body:stmt list; fspan:span }
type top = TopFun of func | TopStmt of stmt
type program = top list
type error = { code:string; message:string; at:span; expected:ty option }
exception Error of error

let type_name = function Int->"Int" | Bool->"Bool" | Str->"Str" | Unit->"Unit"
let mkspan lo hi line column = {lo;hi;line;column}
let fail code message at ?expected () = raise(Error {code;message;at;expected})
let json_string s =
  let b=Buffer.create (String.length s+8) in
  Buffer.add_char b '"';
  String.iter (fun c -> match c with
    | '"' -> Buffer.add_string b "\\\"" | '\\' -> Buffer.add_string b "\\\\"
    | '\n' -> Buffer.add_string b "\\n" | '\r' -> Buffer.add_string b "\\r"
    | '\t' -> Buffer.add_string b "\\t" | '\b' -> Buffer.add_string b "\\b"
    | '\012' -> Buffer.add_string b "\\f"
    | c when Char.code c < 0x20 -> Buffer.add_string b (Printf.sprintf "\\u%04x" (Char.code c))
    | c -> Buffer.add_char b c) s;
  Buffer.add_char b '"'; Buffer.contents b
let pos_json s = Printf.sprintf "{\"offset\":%d,\"line\":%d,\"column\":%d}" s.lo s.line s.column
let span_json s = Printf.sprintf "{\"start\":%s,\"endOffset\":%d}" (pos_json s) s.hi
let expr_span = function EInt(_,s)|EBool(_,s)|EStr(_,s)|EName(_,s)|EHole(_,s)|ECall(_,_,s)|EBin(_,_,_,s)|EIf(_,_,_,s)->s
let stmt_span = function SLet(_,_,_,s)|SReturn(_,s)|SBlock(_,s)|SExpr(_,s)->s
let is_digit c = c>='0'&&c<='9'
let is_alpha c = c>='a'&&c<='z'||c>='A'&&c<='Z'||c='_'
let is_alnum c = is_alpha c || is_digit c

let lex source =
  let n=String.length source and i=ref 0 and line=ref 1 and col=ref 1 in
  let tokens=ref [] in
  let advance () = let c=source.[!i] in incr i; if c='\n' then (incr line;col:=1) else incr col; c in
  let add kind lo ln cl = tokens := {kind;at=mkspan lo !i ln cl} :: !tokens in
  let rec loop () =
    if !i>=n then tokens := {kind=Eof;at=mkspan !i !i !line !col} :: !tokens else
    let c=source.[!i] in
    if c=' '||c='\t'||c='\r'||c='\n' then (ignore(advance());loop())
    else if c='#' || c='/' && !i+1<n && source.[!i+1]='/' then (
      while !i<n && source.[!i]<>'\n' do ignore(advance()) done; loop())
    else let lo= !i and ln= !line and cl= !col in
    if is_alpha c then (
      ignore(advance()); while !i<n && is_alnum source.[!i] do ignore(advance()) done;
      let word=String.sub source lo (!i-lo) in
      if word="_" then add (Hole None) lo ln cl else add (Id word) lo ln cl; loop())
    else if is_digit c then (
      ignore(advance()); while !i<n && is_digit source.[!i] do ignore(advance()) done;
      let raw=String.sub source lo (!i-lo) in
      let value=try Int64.of_string raw with _->fail "PEP_INT_LITERAL_RANGE" "Integer literal is outside the supported Int range" (mkspan lo !i ln cl) () in
      add (Number value) lo ln cl; loop())
    else if c='"' then (
      ignore(advance()); let b=Buffer.create 16 in
      let rec string_loop () =
        if !i>=n then fail "PEP_UNTERMINATED_STRING" "Unterminated string literal" (mkspan lo !i ln cl) ();
        match advance() with
        | '"' -> ()
        | '\\' -> if !i>=n then fail "PEP_UNTERMINATED_STRING" "Unterminated escape" (mkspan lo !i ln cl) () else
          (match advance() with
           | 'n'->Buffer.add_char b '\n'|'r'->Buffer.add_char b '\r'|'t'->Buffer.add_char b '\t'
           | '0'->Buffer.add_char b '\000'|'\\'->Buffer.add_char b '\\'|'"'->Buffer.add_char b '"'
           | _->fail "PEP_INVALID_ESCAPE" "Unsupported string escape" (mkspan lo !i ln cl) ()); string_loop()
        | '\n' -> fail "PEP_NEWLINE_IN_STRING" "String literals cannot contain an unescaped newline" (mkspan lo !i ln cl) ()
        | c -> Buffer.add_char b c; string_loop()
      in string_loop(); add (Text(Buffer.contents b)) lo ln cl; loop())
    else if c='?' then (
      ignore(advance());
      if !i<n && is_alpha source.[!i] then (ignore(advance());while !i<n&&is_alnum source.[!i] do ignore(advance()) done;
        add (Hole(Some(String.sub source (lo+1) (!i-lo-1)))) lo ln cl)
      else add (Hole None) lo ln cl; loop())
    else if c='<' && !i+1<n && source.[!i+1]='=' then (ignore(advance());ignore(advance());add (Sym "<=") lo ln cl;loop())
    else if c='-' && !i+1<n && source.[!i+1]='>' then (ignore(advance());ignore(advance());add (Sym "->") lo ln cl;loop())
    else if List.mem c ['(';')';'{';'}';',';':';';';'+';'-';'*';'/';'='] then
      (ignore(advance());add (Sym(String.make 1 c)) lo ln cl;loop())
    else fail "PEP_UNEXPECTED_CHARACTER" (Printf.sprintf "Unexpected character %C" c) (mkspan lo (lo+1) ln cl) ()
  in loop(); Array.of_list(List.rev !tokens)

type parser = { ts:token array; mutable p:int }
let peek p = p.ts.(p.p)
let take p = let t=peek p in p.p<-min (p.p+1) (Array.length p.ts-1);t
let at p = (peek p).at
let symbol p s = match (peek p).kind with Sym x when x=s->true|_->false
let keyword p s = match (peek p).kind with Id x when x=s->true|_->false
let accept_sym p s = if symbol p s then (ignore(take p);true) else false
let expect_sym p s = if not(accept_sym p s) then fail "PEP_PARSE_EXPECTED" ("Expected '"^s^"'") (at p) ()
let expect_id p = match take p with {kind=Id s;_}->s|t->fail "PEP_PARSE_NAME" "Expected a name" t.at ()
let parse_type p = match take p with
  |{kind=Id "Int";_}->Int |{kind=Id "Bool";_}->Bool |{kind=Id "Str";_}->Str |{kind=Id "Unit";_}->Unit
  |t->fail "PEP_PARSE_TYPE" "Expected Int, Bool, Str, or Unit" t.at ()
let combine a b = mkspan a.lo b.hi a.line a.column
let rec parse_expr p min_prec =
  let first=take p in
  let lhs=match first.kind with
    |Number n->EInt(n,first.at)|Text s->EStr(s,first.at)|Hole h->EHole(h,first.at)
    |Id "true"->EBool(true,first.at)|Id "false"->EBool(false,first.at)
    |Id "if" -> let condition=parse_expr p 0 in expect_sym p "{"; let yes=parse_expr p 0 in ignore(at p); expect_sym p "}";
        if not(keyword p "else") then fail "PEP_PARSE_ELSE" "Expected else after the true branch" (at p) ();
        ignore(take p); expect_sym p "{"; let no=parse_expr p 0 in let ending=at p in expect_sym p "}"; EIf(condition,yes,no,combine first.at ending)
    |Id name -> if accept_sym p "(" then (
        let args=ref [] in if not(symbol p ")") then (args:= [parse_expr p 0];while accept_sym p "," do args:= !args@[parse_expr p 0] done);
        let close=at p in expect_sym p ")"; ECall(name,!args,combine first.at close)) else EName(name,first.at)
    |Sym "(" ->let e=parse_expr p 0 in let close=at p in expect_sym p ")";
        let s=combine first.at close in (match e with EInt(n,_)->EInt(n,s)|EBool(v,_)->EBool(v,s)|EStr(v,_)->EStr(v,s)|EName(n,_)->EName(n,s)|EHole(h,_)->EHole(h,s)|ECall(n,a,_)->ECall(n,a,s)|EBin(o,l,r,_)->EBin(o,l,r,s)|EIf(c,y,n,_)->EIf(c,y,n,s))
    |Sym "-" -> let rhs=parse_expr p 30 in EBin("neg",EInt(0L,first.at),rhs,combine first.at (expr_span rhs))
    |t->fail "PEP_PARSE_EXPRESSION" "Expected an expression" first.at () in
  parse_tail p min_prec lhs
and parse_tail p min_prec lhs =
  let op,prec=match (peek p).kind with Sym "<="->"<=",5|Sym "+"->"+",10|Sym "-"->"-",10|Sym "*"->"*",20|Sym "/"->"/",20|_->"",-1 in
  if prec<min_prec then lhs else (ignore(take p); let rhs=parse_expr p (prec+1) in parse_tail p min_prec (EBin(op,lhs,rhs,combine (expr_span lhs) (expr_span rhs))))
let rec parse_stmt p =
  if keyword p "let" then (
    let start=(take p).at in let name=expect_id p in
    let annotation=if accept_sym p ":" then Some(parse_type p) else None in
    expect_sym p "="; let value=parse_expr p 0 in ignore(accept_sym p ";");
    SLet(name,annotation,value,combine start (expr_span value)))
  else if keyword p "return" then (
    let start=(take p).at in let value=parse_expr p 0 in ignore(accept_sym p ";");
    SReturn(value,combine start (expr_span value)))
  else if symbol p "{" then (
    let start=(take p).at in let body=ref [] in
    while not(symbol p "}") && (peek p).kind<>Eof do body:=parse_stmt p :: !body done;
    let ending=at p in expect_sym p "}"; SBlock(List.rev !body,combine start ending))
  else (
    let e=parse_expr p 0 in ignore(accept_sym p ";"); SExpr(e,expr_span e))
let parse_func p =
  let start=(take p).at in let name=expect_id p in expect_sym p "(";
  let params=ref [] in
  if not(symbol p ")") then (
    let param () = let n=expect_id p in let ns=p.ts.(p.p-1).at in expect_sym p ":";let t=parse_type p in params:= !params@[(n,t,ns)] in
    param();while accept_sym p "," do param() done);
  expect_sym p ")"; expect_sym p "->"; let result=parse_type p in
  let body=match parse_stmt p with SBlock(xs,_)->xs|s->fail "PEP_FUNCTION_BODY" "Expected a braced function body" (stmt_span s) () in
  let ending=p.ts.(p.p-1).at in {fname=name;params= !params;result;body;fspan=combine start ending}
let parse source =
  let p={ts=lex source;p=0} and tops=ref [] in
  while (peek p).kind<>Eof do
    if keyword p "fn" then tops:=TopFun(parse_func p)::!tops else tops:=TopStmt(parse_stmt p)::!tops
  done; List.rev !tops

type binding = { bid:int; bname:string; bty:ty option; bspan:span }
type signature = { fid:int; name:string; params:(string*ty) list; result:ty; decl:func }
type texpr = { node:texpr_node; ety:ty option; espan:span }
and texpr_node = XInt of int64|XBool of bool|XStr of string|XVar of int|XHole of string option|XCall of int option*string*texpr list|XBin of string*texpr*texpr|XIf of texpr*texpr*texpr
type tstmt = TLet of binding*texpr|TReturn of texpr|TBlock of tstmt list|TExpr of texpr
type tfunc = { sig_:signature; tparams:binding list; tbody:tstmt list }
type hole = { hid:string option; hscope:string; hty:ty option; hspan:span; hbindings:binding list }
type checked = { functions:tfunc list; tops:tstmt list; holes:hole list }
let lookup env name = let rec go=function []->None|scope::rest->match List.find_opt(fun b->b.bname=name)scope with Some b->Some b|None->go rest in go env
let has_current env name = match env with scope::_->List.exists(fun b->b.bname=name)scope|[]->false
let visible env =
  let seen=Hashtbl.create 8 in
  List.concat_map (fun scope->List.filter(fun b->if Hashtbl.mem seen b.bname then false else (Hashtbl.add seen b.bname ();true)) scope) env
let candidates ty bs=List.filter(fun b->b.bty=Some ty)bs
let rec ast_expr_json e = let s=span_json(expr_span e) in match e with
 |EInt(n,_)->"{\"kind\":\"int\",\"value\":"^Int64.to_string n^",\"span\":"^s^"}"
 |EBool(v,_)->"{\"kind\":\"bool\",\"value\":"^string_of_bool v^",\"span\":"^s^"}"
 |EStr(v,_)->"{\"kind\":\"string\",\"value\":"^json_string v^",\"span\":"^s^"}"
 |EName(n,_)->"{\"kind\":\"name\",\"name\":"^json_string n^",\"span\":"^s^"}"
 |EHole(h,_)->"{\"kind\":\"hole\",\"name\":"^(match h with None->"null"|Some x->json_string x)^",\"span\":"^s^"}"
 |ECall(n,args,_)->"{\"kind\":\"call\",\"name\":"^json_string n^",\"arguments\":["^String.concat ","(List.map ast_expr_json args)^"],\"span\":"^s^"}"
 |EBin(o,a,b,_)->"{\"kind\":\"binary\",\"operator\":"^json_string o^",\"left\":"^ast_expr_json a^",\"right\":"^ast_expr_json b^",\"span\":"^s^"}"
 |EIf(c,y,n,_)->"{\"kind\":\"if\",\"condition\":"^ast_expr_json c^",\"then\":"^ast_expr_json y^",\"else\":"^ast_expr_json n^",\"span\":"^s^"}"
let rec ast_stmt_json s=match s with
 |SLet(n,t,e,sp)->"{\"kind\":\"let\",\"name\":"^json_string n^",\"annotation\":"^(match t with None->"null"|Some t->json_string(type_name t))^",\"value\":"^ast_expr_json e^",\"span\":"^span_json sp^"}"
 |SReturn(e,sp)->"{\"kind\":\"return\",\"value\":"^ast_expr_json e^",\"span\":"^span_json sp^"}"
 |SBlock(xs,sp)->"{\"kind\":\"block\",\"statements\":["^String.concat ","(List.map ast_stmt_json xs)^"],\"span\":"^span_json sp^"}"
 |SExpr(e,sp)->"{\"kind\":\"expression\",\"value\":"^ast_expr_json e^",\"span\":"^span_json sp^"}"
let ast_json tops = "["^String.concat ","(List.map(function
 |TopFun f->"{\"kind\":\"function\",\"name\":"^json_string f.fname^",\"parameters\":["^String.concat ","(List.map(fun(n,t,s)->"{\"name\":"^json_string n^",\"type\":"^json_string(type_name t)^",\"span\":"^span_json s^"}")f.params)^"],\"returnType\":"^json_string(type_name f.result)^",\"body\":["^String.concat ","(List.map ast_stmt_json f.body)^"],\"span\":"^span_json f.fspan^"}"
 |TopStmt s->ast_stmt_json s)tops)^"]"

let check tops =
  let next_id=ref 0 and next_fid=ref 0 and holes=ref [] in
  let fresh ()=let n= !next_id in incr next_id;n in
  let signatures=Hashtbl.create 16 in
  List.iter(function TopFun f->if f.fname="say" || f.fname="int_text" then fail "PEP_RESERVED_FUNCTION" ("Function name "^f.fname^" is reserved for a builtin") f.fspan () else if Hashtbl.mem signatures f.fname then fail "PEP_DUPLICATE_FUNCTION" ("Duplicate function '"^f.fname^"'") f.fspan () else
    let fid= !next_fid in incr next_fid;Hashtbl.add signatures f.fname {fid;name=f.fname;params=List.map(fun(n,t,_)->n,t)f.params;result=f.result;decl=f}
    |_->())tops;
  let record_hole env scope id expected sp = holes:={hid=id;hscope=scope;hty=expected;hspan=sp;hbindings=visible env}::!holes in
  let rec synth env scope e = match e with
   |EInt(n,s)->{node=XInt n;ety=Some Int;espan=s}
   |EBool(v,s)->{node=XBool v;ety=Some Bool;espan=s}
   |EStr(v,s)->{node=XStr v;ety=Some Str;espan=s}
   |EHole(id,s)->record_hole env scope id None s;{node=XHole id;ety=None;espan=s}
   |EName(n,s)->(match lookup env n with None->fail "PEP_UNKNOWN_VARIABLE" ("Unknown variable '"^n^"'") s ()
      |Some b->(match b.bty with None->fail "PEP_UNCONSTRAINED_BINDING" ("Binding '"^n^"' has no known type") s ()
        |Some t->{node=XVar b.bid;ety=Some t;espan=s}))
   |ECall(n,args,s)->call env scope n args s
   |EBin("<=",a,b,s)->let ta=check_expr env scope (Some Int) a and tb=check_expr env scope (Some Int) b in
      {node=XBin("<=",ta,tb);ety=Some Bool;espan=s}
   |EBin(op,a,b,s)->let ta=check_expr env scope (Some Int) a and tb=check_expr env scope (Some Int) b in
      {node=XBin(op,ta,tb);ety=Some Int;espan=s}
   |EIf(c,y,n,s)->let tc=check_expr env scope (Some Bool) c in
      let then_expr,else_expr=match y,n with
       |EHole _,EHole _->synth env scope y,synth env scope n
       |EHole _,_->let el=synth env scope n in check_expr env scope el.ety y,el
       |_,EHole _->let th=synth env scope y in th,check_expr env scope th.ety n
       |_->let th=synth env scope y in th,check_expr env scope th.ety n in
      (match then_expr.ety,else_expr.ety with Some a,Some b when a<>b->fail "PEP_TYPE_MISMATCH" ("If branches have types "^type_name a^" and "^type_name b) s ()|_->());
      {node=XIf(tc,then_expr,else_expr);ety=(match then_expr.ety with Some _ as t->t|None->else_expr.ety);espan=s}
  and check_expr env scope expected e = match e with
   |EHole(id,s)->record_hole env scope id expected s;{node=XHole id;ety=expected;espan=s}
   |EIf(c,y,n,s)->let tc=check_expr env scope (Some Bool) c in let ty=check_expr env scope expected y and en=check_expr env scope expected n in
      (match ty.ety,en.ety with Some a,Some b when a<>b->fail "PEP_TYPE_MISMATCH" ("If branches have types "^type_name a^" and "^type_name b) s ()|_->());
      {node=XIf(tc,ty,en);ety=(match expected with Some _ as t->t|None->(match ty.ety with Some _ as t->t|None->en.ety));espan=s}
   |_->let t=synth env scope e in (match expected,t.ety with Some want,Some got when want<>got->fail "PEP_TYPE_MISMATCH" ("Expected "^type_name want^" but found "^type_name got) t.espan ~expected:want ()|_->());t
  and call env scope name args s =
    let params,result,fid = if name="say" then [Str],Unit,None else if name="int_text" then [Int],Str,None else
      match Hashtbl.find_opt signatures name with None->fail "PEP_UNKNOWN_FUNCTION" ("Unknown function '"^name^"'") s ()
       |Some f->List.map snd f.params,f.result,Some f.fid in
    if List.length args<>List.length params then fail "PEP_ARGUMENT_COUNT" (Printf.sprintf "Function '%s' expects %d argument(s), found %d" name (List.length params) (List.length args)) s ();
    let checked=List.map2(fun arg ty->check_expr env scope (Some ty) arg)args params in
    {node=XCall(fid,name,checked);ety=Some result;espan=s}
  in
  let rec check_stmts env scope expected xs =
    let rec loop env acc terminated = function
     |[]->List.rev acc,env,terminated
     |s::rest when terminated->fail "PEP_UNREACHABLE" "Statement follows an unconditional return" (stmt_span s) ()
     |SLet(name,annotation,e,sp)::rest ->
       if has_current env name then fail "PEP_DUPLICATE_BINDING" ("Duplicate binding '"^name^"' in this scope") sp ();
       let te=match annotation with Some t->check_expr env scope (Some t) e|None->synth env scope e in
       let ty=match annotation,te.ety with Some t,_->Some t|None,t->t in
       let b={bid=fresh();bname=name;bty=ty;bspan=sp} in
       let env'=(match env with []->[[b]]|h::tl->(b::h)::tl) in
       loop env' (TLet(b,te)::acc) false rest
     |SReturn(e,sp)::rest ->
       if expected=None then fail "PEP_RETURN_OUTSIDE_FUNCTION" "return is only valid inside a function" sp ();
       let te=check_expr env scope expected e in loop env (TReturn te::acc) true rest
     |SExpr(e,_)::rest->let te=synth env scope e in loop env (TExpr te::acc) false rest
     |SBlock(body,_)::rest->let inner,_,term=check_stmts ([]::env) scope expected body in loop env (TBlock inner::acc) term rest
    in loop env [] false xs
  in
  let functions=ref [] in
  List.iter(function TopFun f->
    let sig_=Hashtbl.find signatures f.fname in
    let seen=Hashtbl.create 8 in
    let params=List.map(fun(n,t,s)->if Hashtbl.mem seen n then fail "PEP_DUPLICATE_PARAMETER" ("Duplicate parameter '"^n^"'") s ();Hashtbl.add seen n ();{bid=fresh();bname=n;bty=Some t;bspan=s})f.params in
    let typed,_,terminated=check_stmts [params] f.fname (Some f.result) f.body in
    if f.result<>Unit && not terminated then fail "PEP_MISSING_RETURN" ("Function '"^f.fname^"' must return "^type_name f.result) f.fspan ~expected:f.result ();
    functions:={sig_;tparams=params;tbody=typed}::!functions
   |_->()) tops;
  let global_env=ref [[]] and top_typed=ref [] in
  List.iter(function TopStmt s->let typed,env,_=check_stmts !global_env "<top-level>" None [s] in global_env:=env;top_typed:=List.rev_append typed !top_typed|_->())tops;
  {functions=List.rev !functions;tops=List.rev !top_typed;holes=List.rev !holes}

let rec typed_expr_json e =
 let typ=match e.ety with None->"null"|Some t->json_string(type_name t) in
 let node=match e.node with
 |XInt n->"{\"kind\":\"int\",\"value\":"^Int64.to_string n^"}"
 |XBool b->"{\"kind\":\"bool\",\"value\":"^string_of_bool b^"}"
 |XStr s->"{\"kind\":\"string\",\"value\":"^json_string s^"}"
 |XVar id->"{\"kind\":\"binding\",\"bindingId\":"^string_of_int id^"}"
 |XHole h->"{\"kind\":\"hole\",\"name\":"^(match h with None->"null"|Some x->json_string x)^"}"
 |XCall(fid,n,args)->"{\"kind\":\"call\",\"name\":"^json_string n^",\"functionId\":"^(match fid with None->"null"|Some x->string_of_int x)^",\"arguments\":["^String.concat ","(List.map typed_expr_json args)^"]}"
 |XBin(op,a,b)->"{\"kind\":\"binary\",\"operator\":"^json_string op^",\"left\":"^typed_expr_json a^",\"right\":"^typed_expr_json b^"}"
 |XIf(c,y,n)->"{\"kind\":\"if\",\"condition\":"^typed_expr_json c^",\"then\":"^typed_expr_json y^",\"else\":"^typed_expr_json n^"}" in
 "{\"type\":"^typ^",\"span\":"^span_json e.espan^",\"expression\":"^node^"}"
let rec typed_stmt_json = function
 |TLet(b,e)->"{\"kind\":\"let\",\"name\":"^json_string b.bname^",\"bindingId\":"^string_of_int b.bid^",\"type\":"^(match b.bty with None->"null"|Some t->json_string(type_name t))^",\"value\":"^typed_expr_json e^"}"
 |TReturn e->"{\"kind\":\"return\",\"value\":"^typed_expr_json e^"}"
 |TBlock xs->"{\"kind\":\"block\",\"statements\":["^String.concat ","(List.map typed_stmt_json xs)^"]}"
 |TExpr e->"{\"kind\":\"expression\",\"value\":"^typed_expr_json e^"}"
let typed_json c =
 "{\"functions\":["^String.concat ","(List.map(fun f->"{\"functionId\":"^string_of_int f.sig_.fid^",\"name\":"^json_string f.sig_.name^",\"parameters\":["^String.concat ","(List.map(fun b->"{\"name\":"^json_string b.bname^",\"bindingId\":"^string_of_int b.bid^",\"type\":"^json_string(type_name(Option.get b.bty))^"}")f.tparams)^"],\"returnType\":"^json_string(type_name f.sig_.result)^",\"body\":["^String.concat ","(List.map typed_stmt_json f.tbody)^"]}")c.functions)^"],\"statements\":["^String.concat ","(List.map typed_stmt_json c.tops)^"]}"
let hole_json h =
 let bindings="["^String.concat ","(List.map(fun b->"{\"name\":"^json_string b.bname^",\"bindingId\":"^string_of_int b.bid^",\"type\":"^(match b.bty with None->"null"|Some t->json_string(type_name t))^"}")h.hbindings)^"]" in
 let actions=match h.hty with None->"[]"|Some ty->"[{\"kind\":\"fill_hole\",\"expectedType\":"^json_string(type_name ty)^",\"candidates\":["^String.concat ","(List.map(fun b->"{\"name\":"^json_string b.bname^",\"bindingId\":"^string_of_int b.bid^"}")(candidates ty h.hbindings))^"]}]" in
 "{\"identity\":"^(match h.hid with None->"null"|Some x->json_string x)^",\"scope\":"^json_string h.hscope^",\"expectedType\":"^(match h.hty with None->"null"|Some t->json_string(type_name t))^",\"bindings\":"^bindings^",\"actions\":"^actions^",\"span\":"^span_json h.hspan^"}"
let diag_json d = "{\"schemaVersion\":2,\"status\":\"invalid\",\"diagnostics\":[{\"code\":"^json_string d.code^",\"severity\":\"error\",\"message\":"^json_string d.message^",\"expectedType\":"^(match d.expected with None->"null"|Some t->json_string(type_name t))^",\"span\":"^span_json d.at^"}]}"
let program_status c = if c.holes=[] then "valid" else "incomplete"
let check_json tops c = "{\"schemaVersion\":2,\"status\":"^json_string(program_status c)^",\"ast\":"^ast_json tops^",\"typedTree\":"^typed_json c^",\"holes\":["^String.concat ","(List.map hole_json c.holes)^"],\"diagnostics\":[]}"

type value = VInt of int64|VBool of bool|VStr of string|VUnit
exception Runtime of string*string*span
let runtime code message sp=raise(Runtime(code,message,sp))
let int_value = function VInt n->n|_->assert false
let checked_bin op a b sp =
 let add_over x y = y>0L && x>Int64.sub Int64.max_int y || y<0L && x<Int64.sub Int64.min_int y in
 let sub_over x y = y<0L && x>Int64.add Int64.max_int y || y>0L && x<Int64.add Int64.min_int y in
 let mul_over x y = if x=0L||y=0L then false else if x=Int64.min_int then y= -1L else if y=Int64.min_int then x= -1L else if x>0L then (if y>0L then x>Int64.div Int64.max_int y else y<Int64.div Int64.min_int x) else (if y>0L then x<Int64.div Int64.min_int y else y<Int64.div Int64.max_int x) in
 match op with
 |"<="->VBool(a<=b)
 |"+"->if add_over a b then runtime "PEP_RUNTIME_OVERFLOW" "Integer addition overflow" sp else VInt(Int64.add a b)
 |"-"->if sub_over a b then runtime "PEP_RUNTIME_OVERFLOW" "Integer subtraction overflow" sp else VInt(Int64.sub a b)
 |"*"->if mul_over a b then runtime "PEP_RUNTIME_OVERFLOW" "Integer multiplication overflow" sp else VInt(Int64.mul a b)
 |"/"->if b=0L then runtime "PEP_RUNTIME_DIVISION_BY_ZERO" "Division by zero" sp else if a=Int64.min_int&&b= -1L then runtime "PEP_RUNTIME_OVERFLOW" "Integer division overflow" sp else VInt(Int64.div a b)
 |"neg"->if b=Int64.min_int then runtime "PEP_RUNTIME_OVERFLOW" "Integer negation overflow" sp else VInt(Int64.neg b)
 |_ ->assert false
let execute c =
 let fs=Hashtbl.create 16 in List.iter(fun f->Hashtbl.add fs f.sig_.fid f)c.functions;
 let max_depth=512 in
 let rec eval env callstack e = match e.node with
  |XInt n->VInt n|XBool b->VBool b|XStr s->VStr s
  |XVar id->(try List.assoc id env with Not_found->runtime "PEP_RUNTIME_UNRESOLVED_BINDING" "Checked binding is missing at runtime" e.espan)
  |XHole _->runtime "PEP_RUNTIME_HOLE" "Cannot execute an incomplete expression" e.espan
  |XBin(op,a,b)->let va=int_value(eval env callstack a) and vb=int_value(eval env callstack b) in checked_bin op va vb e.espan
  |XIf(c,y,n)->(match eval env callstack c with VBool true->eval env callstack y|VBool false->eval env callstack n|_->assert false)
  |XCall(fid,name,args)->let values=List.map(eval env callstack)args in
    if name="say" then (match values with [VStr s]->print_endline s;VUnit|_->assert false)
    else if name="int_text" then (match values with [VInt n]->VStr(Int64.to_string n)|_->assert false)
    else match fid with None->runtime "PEP_RUNTIME_UNKNOWN_CALL" ("Unknown checked call '"^name^"'") e.espan|Some id->
      if List.length callstack>=max_depth then runtime "PEP_RUNTIME_CALL_DEPTH" "Maximum function call depth exceeded" e.espan;
      let f=Hashtbl.find fs id in let env'=List.map2(fun b v->b.bid,v)f.tparams values in
      (match exec_stmts env' (name::callstack) f.tbody with Some v->v|None->VUnit)
 and exec_stmts env stack = function
  |[]->None
  |TLet(b,e)::rest->let v=eval env stack e in exec_stmts ((b.bid,v)::env) stack rest
  |TReturn e::_->Some(eval env stack e)
  |TBlock xs::rest->(match exec_stmts env stack xs with Some v->Some v|None->exec_stmts env stack rest)
  |TExpr e::rest->ignore(eval env stack e);exec_stmts env stack rest
 in ignore(exec_stmts [] [] c.tops)

let read_file path = let ic=open_in_bin path in Fun.protect ~finally:(fun()->close_in ic)(fun()->really_input_string ic (in_channel_length ic))
let usage () = prerr_endline "usage: pep describe [--json] | inspect|check|run FILE [--json] | query FILE --holes --json [--offset N]";exit 2
let () =
 try
  let args=Array.to_list Sys.argv |> List.tl in
  match args with
  |["describe"]|["describe";"--json"]->print_endline "{\"schemaVersion\":2,\"language\":\"Pep\",\"types\":[\"Int\",\"Bool\",\"Str\",\"Unit\"],\"features\":[\"functions\",\"recursion\",\"lexical_scopes\",\"typed_holes\",\"query_holes\",\"checked_integer_arithmetic\",\"interpreter\"],\"builtins\":[{\"name\":\"say\",\"parameters\":[\"Str\"],\"returns\":\"Unit\"},{\"name\":\"int_text\",\"parameters\":[\"Int\"],\"returns\":\"Str\"}]}"
  |command::file::flags when List.mem command ["inspect";"check";"run";"query"] ->
    let source=read_file file in let tops=parse source in
    if command="inspect" then print_endline("{\"schemaVersion\":2,\"status\":\"parsed\",\"ast\":"^ast_json tops^"}") else
    let checked=check tops in
    if command="query" then (
      let holes=if List.mem "--holes" flags then checked.holes else checked.holes in
      let selected=match List.find_index (fun x->x="--offset") flags with None->holes|Some i->
        if i+1>=List.length flags then usage();let off=try int_of_string(List.nth flags (i+1))with _->usage() in List.filter(fun h->h.hspan.lo=off)holes in
      if selected=[] && List.exists(fun f->f="--offset")flags then (print_endline("{\"schemaVersion\":2,\"status\":"^json_string(program_status checked)^",\"holes\":[]}");exit 1);
      print_endline("{\"schemaVersion\":2,\"status\":"^json_string(program_status checked)^",\"holes\":["^String.concat ","(List.map hole_json selected)^"]}"))
    else if command="check" then (print_endline(check_json tops checked);if checked.holes<>[] then exit 1)
    else if checked.holes<>[] then (if List.mem "--json" flags then print_endline(check_json tops checked) else prerr_endline "incomplete: unresolved typed holes";exit 1)
    else execute checked
  |_ ->usage()
 with
 |Error d->if Array.exists((=)"--json")Sys.argv then print_endline(diag_json d) else prerr_endline(Printf.sprintf "%s:%d:%d: %s: %s" (List.hd(Array.to_list Sys.argv)) d.at.line d.at.column d.code d.message);exit 1
 |Runtime(code,message,sp)->if Array.exists((=)"--json")Sys.argv then print_endline("{\"schemaVersion\":2,\"status\":\"runtime_error\",\"diagnostics\":[{\"code\":"^json_string code^",\"severity\":\"error\",\"message\":"^json_string message^",\"span\":"^span_json sp^"}]}") else prerr_endline(Printf.sprintf "%d:%d: %s: %s" sp.line sp.column code message);exit 1
 |Sys_error m->prerr_endline m;exit 2
