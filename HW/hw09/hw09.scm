(define (curry-cook formals body)
  ; Base Case: If there is only one formal argument left.
  (if (= (length formals) 1)
      ; Construct the innermost lambda: (lambda (arg) body)
      `(lambda (,(car formals)) ,body)

      ; Recursive Step: If there are multiple formals.
      ; Take the first formal and wrap the curried version of the rest.
      `(lambda (,(car formals))
         ,(curry-cook (cdr formals) body))))

(define (curry-consume curry args)
  'YOUR-CODE-HERE)

(define-macro (switch expr options)
  (switch-to-cond (list 'switch expr options)))

(define (switch-to-cond switch-expr)
  (cons _________
        (map (lambda (option)
               (cons _______________ (cdr option)))
             (car (cdr (cdr switch-expr))))))
